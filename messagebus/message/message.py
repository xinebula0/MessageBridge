from flask import jsonify, g
from flask.views import MethodView, request
from sqlalchemy import select
from messagebus.models import RoutingRule, MessageSchema
from messagebus.mbc import MessageBus, ConnectorFactory
from messagebus import db
import logging

logger = logging.getLogger('MBus')


class MessageView(MethodView):
    def post(self):
        # 获取 JSON 数据
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        schema = MessageSchema()
        message = schema.load(data.get('Message'))

        stmt = select(RoutingRule).where(RoutingRule.channel.in_(message.channels),
                                         RoutingRule.sender == message.sender)

        results = db.session.execute(stmt).scalars()
        db.session.commit()
        channels = list()
        for result in results:
            if result.channel not in channels:
                channels.append(result.channel)
                conn = ConnectorFactory.get_connector(result.channel)

            message.recipients.append(result.recipient)
        if len(channels) != len(message.channels):
            logger.error(f"Invalid channel found: {message.channels}")
            return jsonify({"error": "Invalid channel found"}), 400
        db.session.add(message)
        db.session.commit()

        for rule in results:
            g.mbus.add_routing_rule(rule)
            connector = ConnectorFactory(name=message.sender, channel=rule.channel)
            g.mbus.register_connector(connector)

        g.mbus.send_message(message)
        return jsonify({"message": "Message sent"}), 200
