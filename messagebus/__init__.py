from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask import Flask, g
import yaml
import logging.config
from messagebus.mbc import MessageBus
from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger('MBus')

class Base(DeclarativeBase):
    pass


# 创建数据库实例
db = SQLAlchemy(model_class=Base)


def create_app():
    app = Flask(__name__)
    with open('conf/messagebus.yaml', 'r') as f:
        config = yaml.safe_load(f)
        app.config.update(config)

    # 加载 YAML 日志配置
    with open('logging.yaml', 'r') as f:
        log_config = yaml.safe_load(f)
        logging.config.dictConfig(log_config)

    db.init_app(app)

    # 注册蓝图到应用
    from messagebus.message import message_bp
    app.register_blueprint(message_bp)

    # 定于全局处理
    @app.before_request
    def create_session():
        g.mbus = MessageBus()

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
