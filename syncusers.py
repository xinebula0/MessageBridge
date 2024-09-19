import logging.config
from flask import Flask, g
import yaml
from requests import Session
from sqlalchemy import select, delete, update
import math
from datetime import datetime, timezone
import uuid
from messagebus import db

app = Flask(__name__)
with app.app_context():
    # 加载 YAML 日志配置
    g.uuid = uuid.uuid4()
        
    with open('conf/logging.yaml', 'r') as f:
        log_config = yaml.safe_load(f)
        logging.config.dictConfig(log_config)

    logger = logging.getLogger('MBus')
    logger.info("Logging configured")

    with open('conf/messagebus.yaml', 'r') as f:
        config = yaml.safe_load(f)
        app.config.update(config)
    logger.info("Config loaded")

    from messagebus.models import Recipient, RecipientSchema
    db.init_app(app)
    db.create_all()

    # Keycloak 服务器地址和 realm 名称
    keycloak = app.config.get("keycloak")
    KEYCLOAK_SERVER = keycloak["host"]
    REALM_NAME = keycloak["realm"]

    # 客户端凭据（需要替换为实际值）
    CLIENT_ID = keycloak["client_id"]
    CLIENT_SECRET = keycloak["client_secret"]
    PAGE_SIZE = keycloak["pagesize"]

    # 获取 token 的 URL
    token_url = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/token"

    # 请求 token 所需的参数
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'openid profile'
    }

    session = Session()
    cafile = keycloak.get("cert")
    if cafile:
        session.verify = cafile
    else:
        session.verify = False
    # 请求 token
    response = session.post(token_url, data=token_data)
    token = response.json().get('access_token')
    logger.info(f"Get token successfully.")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    session.headers.update(headers)

    # 获取全部用户信息
    url = f"{KEYCLOAK_SERVER}/admin/realms/{REALM_NAME}/users/count"
    response = session.get(url)
    all_user_number = response.json()

    url = f"{KEYCLOAK_SERVER}/admin/realms/{REALM_NAME}/users"
    users = list()
    for i in range(math.ceil(all_user_number / PAGE_SIZE)):
        response = session.get(url, params={"max": PAGE_SIZE, "first": i * PAGE_SIZE})
        users.extend(response.json())

    # 用户清理
    stmt = select(Recipient).where(Recipient.is_group.is_(False))
    recipients = db.session.execute(stmt).scalars().all()
    refs_a = [recipient.employee_id for recipient in recipients]
    refs_b = [user["username"] for user in users]
    targets = list(set(refs_a) - set(refs_b))
    if targets:
        stmt = delete(Recipient).where(Recipient.employee_id.in_(targets))
        db.session.execute(stmt)
        db.session.commit()
        logger.info(f"Warning! 用户{targets}已清理")

    # 用户同步
    newbies = list(set(refs_b) - set(refs_a))
    schema = RecipientSchema()

    for user in users:
        if "st-wg-" in user['username']:
            monkeytalk_id = user['username']
        else:
            monkeytalk_id = None
        if user["username"] in newbies:
            recipient = Recipient(name=user['attributes']['displayName'][0],
                                  is_group=False,
                                  employee_id=user['username'],
                                  monkeytalk=monkeytalk_id,
                                  email=user['email'],
                                  bocsms=None,
                                  last_updated=None)
            db.session.add(recipient)
            db.session.commit()
            logger.info(f'{schema.dump(recipient)} has been added.')
        else:
            last_updated = datetime.strptime(user['attributes']['modifyTimestamp'][-1], '%Y%m%d%H%M%SZ')
            created_at = datetime.fromtimestamp(user['createdTimestamp']/1000)
            for recipient in recipients:
                if last_updated >= recipient.last_updated:
                    stmt = update(Recipient).where(
                        Recipient.employee_id == user['username']
                    ).values(
                        email=user['email'],
                        name=user['attributes']['displayName'][0],
                        last_updated=datetime.now(timezone.utc)
                    )
                    db.session.execute(stmt)
                    db.session.commit()
                    logger.info(f'{schema.dump(recipient)} has been updated.')
    logger.info(f"本次同步已完成于{datetime.now()}")
