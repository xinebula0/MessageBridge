from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask import (Flask, g, has_request_context,
                   has_app_context, jsonify)
import yaml
import logging.config
from cryptography.fernet import Fernet
import os
import logging
import uuid
from werkzeug.exceptions import HTTPException
from flask_swagger_ui import get_swaggerui_blueprint

logger = logging.getLogger('MBus')


class Base(DeclarativeBase):
    pass


# 创建数据库实例
db = SQLAlchemy(model_class=Base)


def create_app(name):
    app = Flask(name)
    with open('conf/messagebus.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        app.config.update(config)

    # 加载 YAML 日志配置
    with open('conf/logging.yaml', 'r', encoding='utf-8') as f:
        log_config = yaml.safe_load(f)
        logging.config.dictConfig(log_config)

    # 关闭watchdog的debug信息
    logging.getLogger("watchdog").setLevel(logging.INFO)

    db.init_app(app)

    # 注册蓝图到应用
    from messagebus.message import message_bp
    app.register_blueprint(message_bp)

    @app.before_request
    def create_mbus():
        from messagebus.mbc import MessageBus, ConnectorFactory
        g.mbus = MessageBus()
        g.uuid = str(uuid.uuid4())
        channels = app.config.get("channels")
        for channel in app.config["inuse"]:
            conf = channels[channel]["default"]
            conn = ConnectorFactory.get_connector(channel, **conf)
            g.mbus.register_connector(conn)

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        # 如果是HTTP异常，获取状态码和描述信息
        response = e.get_response()
        response.data = jsonify({
            "code": e.name,
            "message": e.description
        }).data
        response.content_type = "application/json"
        return response

    # Swagger setting
    swagger_url = '/apidoc'
    api_url = '/static/swagger.yaml'
    swaggerui_blueprint = get_swaggerui_blueprint(swagger_url, api_url)
    app.register_blueprint(swaggerui_blueprint, url_preifx=swagger_url)

    return app


class TransIdFilter(logging.Filter):
    def filter(self, record):
        record.uuid = getattr(g, 'uuid', 'N/A')
        return True


def decrypt(password):
    if os.getenv("MASTER_KEY"):
        MASTER_KEY = bytes(os.getenv("MASTER_KEY").encode("utf-8"))
    else:
        logger.error("Error! MASTER_KEY not found, now using default key")
        MASTER_KEY = b"ThisIsTheMasterKey"
    cipher_suite = Fernet(MASTER_KEY)
    return cipher_suite.decrypt(password).decode("utf-8")


class UUIDFilter(logging.Filter):
    def filter(self, record):
        # 使用固定的 UUID
        if has_request_context() or has_app_context():
            record.uuid = getattr(g, 'uuid', 'N/A')
        else:
            record.uuid = 'N/A'

        return True
