from flask import Blueprint
from .message import MessageView


message_bp = Blueprint('message', __name__)

# 实例化 MessageView 类
message_view = MessageView.as_view('message_view')

# 注册视图函数到蓝图
message_bp.add_url_rule('/message/', view_func=message_view, methods=['POST'])