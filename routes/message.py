from flask import jsonify, g
from flask.views import MethodView, request
from sqlalchemy import select
from components.database import RoutingRule
from components.mbc import MessageBus, Connector, Message


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
        g.db_session.commit()

        mbus = MessageBus()
        message = Message(content, receivers, title=title, timestamp=timestamp)
        g.db_session.add(message)
        g.db_session.commit()

        for rule in results:
            mbus.add_routing_rule(rule)
            connector = Connector(name=sender, channel=rule.channel)
            mbus.register_connector(connector)

        mbus.send_message(message, sender)
        return jsonify({"message": "Message sent"}), 200






