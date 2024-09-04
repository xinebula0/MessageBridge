import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from abc import ABC, abstractmethod
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from requests import Session
import base64

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

    def add_routing_rule(self, routing_rule):
        """添加一个路由规则"""
        self.routing_rules.append(routing_rule)

    def send_message(self, message):
        """将消息通过注册的连接器进行发送"""
        for connector in self.connectors:
            transformed_message = self._apply_transformations(message, connector)
            connector.send(transformed_message)

    def receive_message(self, connector_name):
        """从指定的连接器接收消息"""
        connector = self._find_connector_by_name(connector_name)
        if connector:
            message = connector.receive()
            self.route_message(message)
        else:
            raise ValueError(f"Connector {connector_name} not found")

    def route_message(self, message):
        """根据路由规则将消息发送到目标连接器"""
        for rule in self.routing_rules:
            if rule.is_match(message):
                destination_connector = self._find_connector_by_name(rule.destination_connector)
                if destination_connector:
                    transformed_message = self._apply_transformations(message, destination_connector)
                    destination_connector.send(transformed_message)

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
        print(f"{self.name} disconnected")

    @abstractmethod
    def send(self, message):
        """发送消息"""
        pass


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

    def send(self, message):
        # 发送邮件
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
        ciphertext = base64.b64decode(public_key.encrypt(bytes(self.password.encode("utf-8")),
                                                         padding.PKCS1v15())
                                      ).decode("utf-8")
        self.ciphertext = ciphertext

    def connect(self):
        # 连接到 MonkeyTalk 服务器并获取token
        self.refresh_token()
        logger.debug(f"Connected to MonkeyTalk server {self.baseurl}")

    def send(self, message):
        # 发送消息到 MonkeyTalk
        url = f"{self.baseurl}/oa/message/send"
        recipients = self.recipient_filter(message.recipients)
        response = self.session.post(url, json={'content': message.content,
                                                'userLists': recipients})
        response.raise_for_status()

        logger.debug(f"Message sent to MonkeyTalk")

    def recipient_filter(self, users):
        url = f"{self.baseurl}/oa/getFollowers/{self.user}"
        response = self.session.get(url)
        response.raise_for_status()
        followers = [follower.username for follower in response.json().get('data')]

        diff = list(set(users) - set(followers))
        if diff:
            logger.error(f"Recipient {diff} not found in MonkeyTalk.")
            recipients = list(set(users) - set(diff))
        else:
            recipients = users.copy()

        return recipients

    def refresh_token(self):
        url = f"{self.baseurl}/sysUserLogin"
        response = self.session.post(url, json={'user': self.user, 'password': self.ciphertext},
                                     headers={'Client-Version': '1.4.4'})
        if response.status_code == 200:
            self.token = response.json().get('token')
            self.session.headers.update({"Authorization": self.token})
        else:
            logger.error("ERROR! Get token failed.")
            response.raise_for_status()

    def disconnect(self):
        # 关闭连接
        self.token = None
        self.session.close()
        logger.debug("Disconnected from MonkeyTalk server")


class ConnectorFactory:
    @staticmethod
    def get_connector(conn, *args, **kwargs):
        if conn == "email":
            return EmailConnector(*args, **kwargs)
        if conn == "monkeytalk":
            return MonkeyTalkConnector(*args, **kwargs)
        else:
            raise ValueError(f"Unknown database type: {conn}")