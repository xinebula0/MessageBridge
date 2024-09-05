import logging.config
from flask import Flask
import yaml
from sqlalchemy import select


logger = logging.getLogger('MBus')
app = Flask(__name__)

# 加载 YAML 日志配置
with open('logging.yaml', 'r') as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)
    logger.info("Logging configured")

with open('conf/messagebus.yaml', 'r') as f:
    config = yaml.safe_load(f)
    app.config.update(config)
    logger.info("Config loaded")

with (app.app_context()):
    from messagebus.models import db, Recipient, RecipientGroup, RoutingRule, Message
    db.create_all()
    logger.info("Database tables created")

    # 访问keycloak获取全部用户
    users = list()

    # 获取现有用户
    stmt = select(Recipient).where(Recipient.is_group.is_(False))
    recipients = db.session.execute(stmt).scalars().all()
    for recipient in recipients:
        if recipient.employee_id not in users:
            db.session.delete(recipient)
            db.commit()
            logger.info(f"Delete user name: {recipient.name}, "
                        f"employee id: {recipient.employee_id}")

    for user in users:
        if user not in recipients:
            recipient = Recipient(name=user['name'], is_group=False, employee_id=user['employee_id'],
                                  monkeytalk=user['monkeytalk'], email=user['email'], bocsms=user['bocsms'])
            db.session.add(recipient)
            db.commit()
            logger.info(f"Add user name: {recipient.name}, "
                        f"employee id: {recipient.employee_id}")

