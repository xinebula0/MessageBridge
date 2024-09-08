import logging.config
from flask import Flask
import yaml
from requests import Session
from sqlalchemy import select

app = Flask(__name__)
with (app.app_context()):
    # 加载 YAML 日志配置
    with open('conf/logging.yaml', 'r') as f:
        log_config = yaml.safe_load(f)
        logging.config.dictConfig(log_config)

    logger = logging.getLogger('MBus')
    logger.info("Logging configured")

    with open('conf/messagebus.yaml', 'r') as f:
        config = yaml.safe_load(f)
        app.config.update(config)
    logger.info("Config loaded")

    from messagebus.models import db, Recipient
    db.init_app(app)


    # Keycloak 服务器地址和 realm 名称
    keycloak = app.config.get("keycloak")
    KEYCLOAK_SERVER = keycloak["host"]
    REALM_NAME = keycloak["realm"]

    # 客户端凭据（需要替换为实际值）
    CLIENT_ID = keycloak["client_id"]
    CLIENT_SECRET = keycloak["client_secret"]

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
    cafile = app.config["keycloak"].get("cert")
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

    url = f"{KEYCLOAK_SERVER}/admin/realms/{REALM_NAME}/users/count"
    response = session.get(url)
    all_user_number = response.json()

    url= f"{KEYCLOAK_SERVER}/admin/realms/{REALM_NAME}/users"
    response = session.get(url, params={"max": 200})
    data = response.json()

    # 同步新增用户
    stmt = select(Recipient)

    # 同步修改用户


    # 同步删除用户



