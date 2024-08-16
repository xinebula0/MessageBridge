from flask import jsonify, g
from flask.views import MethodView, request
from sqlalchemy import select
from components.database import RoutingRule


class MessageView(MethodView):
    def post(self):
        # 获取 JSON 数据
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        title = data.get("title")
        content = data.get("content")
        sender = data.get("sender", None)
        receivers = data.get("receivers", [])
        timestamp = data.get("timestamp", None)
        channels = data.get("channels", [])

        stmt = select(RoutingRule).where(RoutingRule.channel.in_(channels),
                                         RoutingRule.sender == sender)
        results = g.db_session.execute(stmt).scalars()
        for rule in results:
            rule.send_message(title, content, receivers, timestamp)




