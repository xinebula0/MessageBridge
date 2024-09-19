import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from requests import Session
from sqlalchemy import select
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from flask import render_template, current_app, abort
from messagebus import db
from messagebus.models import Token

# from messagebus import decrypt

logger = logging.getLogger('MBus')


class MessageBus:
    """ 消息总线
        管理所有连接器并处理消息的路由和传输。它可以注册连接器、接收消息、发送消息以及根据路由规则将消息路由到适当的目标。
        允许同步和异步方式调用
    """

    def __init__(self):
        self.connectors = []
        self.routing_rules = []

    def register_connector(self, connector):
        """注册一个新的连接器"""
        self.connectors.append(connector)

    def send(self, conn, message, recipients):
        """将消息通过注册的连接器进行发送"""
        connector = self._find_connector_by_name(conn)
        if not connector:
            logger.error(f"Connector {conn} not found.")
            return
        with connector as conn:
            conn.send(message, recipients)

    def _apply_transformations(self, message, connector):
        """应用消息转换规则（如有必要）"""
        if hasattr(connector, 'transformation_rule'):
            return message.transform(connector.transformation_rule)
        return message

    def _find_connector_by_name(self, name):
        """根据名称查找连接器"""
        for connector in self.connectors:
            if connector.name == name:
                return connector
        return None


class Connector(ABC):
    @abstractmethod
    def connect(self):
        """连接到消息中间件或平台"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        print(f"{self} disconnected")

    @abstractmethod
    def send(self, message, recipients):
        """发送消息"""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class EmailConnector(Connector):
    def __init__(self, smtp, port, email, password):
        self.name = "email"
        self.smtp = smtp
        self.port = port
        self.email = email
        self.password = password
        self.connector = None

    def connect(self):
        # 连接到邮件服务器
        self.connector = smtplib.SMTP(self.smtp, self.port)
        self.connector.starttls()  # 启用安全连接
        self.connector.login(self.email, self.password)  # 登录
        logger.debug(f"Connected to email server {self.smtp}")

    def send(self, message, recipients):
        # 发送邮件
        self.connector.connect()
        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = message.recipient
        msg['Subject'] = message.title
        msg.attach(MIMEText(message.content, 'plain'))
        for sender in message.recipients:
            if sender == message.sender:
                self.connector.send_message(msg)
                logger.debug(f"Email sent to {message.recipient}")
        self.connector.send_message(msg)
        logger.debug(f"Email sent to {message.recipient}")
        self.connector.disconnect()

    def disconnect(self):
        # 断开连接
        self.connector.quit()
        logger.debug("Disconnected from email server")


class MonkeyTalkConnector(Connector):
    """
    api/sys/users/my
    oa/getFollowers/{id}
    sysUserLogin
    /oa/message/send
    """

    def __init__(self, baseurl, user, password, cert):
        self.name = "monkeytalk"
        self.baseurl = baseurl
        self.user = user
        self.password = password
        self.cert = cert
        self.token = None
        self.session = Session()
        self.session.headers.update({"Content-Type": "application/json"})
        with open(self.cert, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        ciphertext = base64.b64encode(public_key.encrypt(bytes(self.password.encode("utf-8")),
                                                         padding.PKCS1v15())
                                      ).decode("utf-8")
        self.ciphertext = ciphertext

    def connect(self):
        # 连接到 MonkeyTalk 服务器并获取token
        self.refresh_token()
        logger.debug(f"Connected to MonkeyTalk server {self.baseurl}.")

    def send(self, message, recipients):
        # 发送消息到 MonkeyTalk
        url = f"{self.baseurl}/oa/message/send"
        # receivers = self.recipient_filter(recipients)
        receivers = recipients
        if Path(f"{current_app.template_folder}/{message.category}.j2").exists():
            content = render_template(f"{message.category}.j2", message=message)
        else:
            content = message.content
        response = self.session.post(url, json={'content': content,
                                                'userLists': receivers})
        response.raise_for_status()
        logger.info(response.json())
        if response.json().get('code') == 200:
            logger.info(f"Message has been sent to {receivers}")
        else:
            logger.error(f"Server has failed for [{response.json().get("msg")}]")
            abort(response.json().get("code"), response.json().get("msg"))

    def recipient_filter(self, users):
        url = f"{self.baseurl}/oa/getFollowers/16288"
        response = self.session.get(url)
        response.raise_for_status()
        logger.debug(response.json())
        followers = [follower["username"] for follower in response.json().get('data')]

        diff = list(set(users) - set(followers))
        if diff:
            logger.error(f"Recipient {diff} not found in MonkeyTalk.")
            recipients = list(set(users) - set(diff))
        else:
            recipients = users

        return recipients

    def refresh_token(self):
        url = f"{self.baseurl}/sysUserLogin"
        response = self.session.post(url, json={'username': self.user, 'password': self.ciphertext},
                                     headers={'Client-Version': '1.4.4'})
        response.raise_for_status()
        if response.json().get("code") == 200:
            self.token = response.json().get('token')
            self.session.headers.update({"Authorization": self.token})
        else:
            logger.error(f"ERROR! Get token failed. [{response.json().get("msg")}]")
            abort(response.json().get("code"), response.json().get("msg"))

    def disconnect(self):
        # 关闭连接
        self.token = None
        self.session.close()
        logger.debug("Disconnected from MonkeyTalk server")


class BocWeChat(Connector):

    def __init__(self, baseurl, tokenurl, cert, client_id, client_secret):
        self.baseurl = baseurl
        self.cert = cert
        self.tokenurl = tokenurl
        self.client_id = client_id
        self.client_secret = client_secret
        self.name = "bocwechat"
        self.session = Session()

    def connect(self):
        # 连接到服务器并获取token
        self.refresh_token()
        logger.debug(f"Connected to BocWeChat server {self.baseurl}.")

    def send(self, message, recipients):
        """发送消息

        Args:
            message (Message): 消息对象
            recipients (list): 接收者列表
        """
        # receivers = self.recipient_filter(recipients)
        receivers = recipients
        if Path(f"{current_app.template_folder}/{message.category}.j2").exists():
            content = render_template(f"{message.category}.j2", message=message)
        else:
            content = message.content
        targets = [{"targetType": "individual", "targetId": tid} for tid in receivers]
        response = self.session.post(self.baseurl, json={'content': content,
                                                         'type': "text",
                                                         'targets': targets})
        response.raise_for_status()
        logger.info(response.json())
        if response.json().get('status') == 200:
            logger.info(f"Message has been sent to {receivers}")
        else:
            logger.error(f"Server has failed for [{response.json().get("data")}]")
            abort(response.json().get("status"), response.json().get("data"))

    def refresh_token(self):
        stmt = select(Token).where(Token.channel == self.name)
        row = db.session.execute(stmt).scalar()
        if row and row.expired_at > datetime.now():
            access_token = row.access_token
            logger.debug("Token no need to update.")
        else:
            params = {"client_id": self.client_id,
                      "client_secret": self.client_secret,
                      "grant_type": "client_credentials"}
            print(self.cert)
            print(self.cert is True)
            response = self.session.post(self.tokenurl, params=params, verify=self.cert if self.cert else False)
            response.raise_for_status()
            resp = response.json()
            logger.debug(resp)

            expired_at = datetime.now() + timedelta(seconds=resp.get("expires_in"))
            token_type = resp.get("token_type")
            access_token = resp.get("access_token")
            token = Token(channel=self.name,
                          access_token=access_token,
                          token_type=token_type,
                          refresh_token=None,
                          expired_at=expired_at)
            db.session.merge(token)
            logger.debug("Token has been updated.")
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def disconnect(self):
        self.token = None
        self.session.close()
        logger.debug("Disconnected from BocWeChat server")


class ConnectorFactory:
    @staticmethod
    def get_connector(conn, *args, **kwargs):
        if conn == "email":
            return EmailConnector(kwargs["smtp"],
                                  kwargs["port"],
                                  kwargs["email"],
                                  kwargs["password"])
        elif conn == "monkeytalk":
            return MonkeyTalkConnector(kwargs["baseurl"],
                                       kwargs["user"],
                                       kwargs["password"],
                                       kwargs["cert"])
        elif conn == "bocwechat":
            print(kwargs)
            return BocWeChat(kwargs["baseurl"],
                             kwargs["tokenurl"],
                             kwargs["cert"],
                             kwargs["client_id"],
                             kwargs["client_secret"])
        else:
            raise ValueError(f"Unknown connection type: {conn}")
