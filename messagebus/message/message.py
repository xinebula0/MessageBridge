from flask import jsonify, g, request
from flask.views import MethodView
from sqlalchemy import select, update
from messagebus.models import Subscription, MessageSchema, Recipient, Message
from messagebus import db
import logging
from werkzeug.exceptions import BadRequest, UnprocessableEntity
from croniter import croniter
from datetime import datetime

logger = logging.getLogger('MBus')


class MessageView(MethodView):
    def post(self):
        # 获取 JSON 数据
        data = request.get_json()

        if not data:
            logger.error("The request has no data provided!")
            raise BadRequest("No data provided")

        schema = MessageSchema()
        message = schema.load(data.get('Message'))
        extra = data.get("extra")
        recipients_in_channel = dict()
        message.uuid = g.uuid
        message.status = "created"
        db.session.add(message)
        db.session.commit()
        logger.info(f"【{message.title}】 from {message.sender} has been created.")

        stmt = select(Subscription).where((Subscription.sender == message.sender)
                                          &
                                          (Subscription.category == message.category)
                                          &
                                          Subscription.is_active.is_(True))
        subscriptions = db.session.execute(stmt).scalars().all()

        if not subscriptions:
            logger.info(f"{message.sender} with {message.category} has no subscription.")
            if extra:
                recipients_in_channel = extra
            else:
                raise UnprocessableEntity(f"{message.sender} with {message.category} has no recipient.")
        else:
            wishlist = dict()
            for subscription in subscriptions:
                if not is_time_in_crontab(subscription.cronexpress):
                    logger.info(f"【{message.title}】 "
                                f"from {message.sender} "
                                f"has been filtered by {subscription.recipient}")
                    continue
                wishlist.setdefault(subscription.channel, []).append(subscription.recipient)

            # 获取各发送渠道所对应的所有订阅者
            for channel, recipients in wishlist.items():
                stmt = select(Recipient).where(Recipient.id.in_(recipients))
                receivers = db.session.execute(stmt).scalars().all()
                for receiver in receivers:
                    if receiver.is_group:
                        for member in receiver.members:
                            if member.active:
                                recipients.append(member.recipient)
                recipients = list(set(wishlist[channel]))

                # 获取各channel的订阅者的对应的接收信息
                stmt = select(Recipient).where(Recipient.id.in_(recipients))
                receivers = db.session.execute(stmt).scalars().all()
                for receiver in receivers:
                    if not receiver.is_group:
                        if getattr(receiver, channel) is None:
                            logger.error(f"{receiver.name} has invalid {channel} channel.")
                            continue
                        recipients_in_channel.setdefault(channel, []).append(getattr(receiver, channel))

            # 合并发送人员
            if recipients_in_channel:
                if extra:
                    for channel, recipients in extra.items():
                        if channel in recipients_in_channel:
                            recipients_in_channel[channel].extend(recipients)
                        else:
                            recipients_in_channel[channel] = recipients
            else:
                recipients_in_channel = extra

        if not recipients_in_channel:
            raise UnprocessableEntity(f"{message.sender} with {message.category} has no recipient.")

        for channel, recipients in recipients_in_channel.items():
            if recipients:
                g.mbus.send(channel, message, recipients)
            else:
                return jsonify({"message": f"Message {message.uuid} has no recipient in {channel}.",
                                "code": "warning"}), 200

        stmt = update(Message).where(
            Message.uuid == message.uuid
        ).values(
            sent_at=datetime.now(),
            status="completed"
        )
        db.session.execute(stmt)
        db.session.commit()

        return jsonify({"message": f"Message {message.uuid} has been sent.",
                        "code": "ok"}), 200


def is_time_in_crontab(cron_expression):
    """
    判断给定的时间是否落入crontab表达式内

    :param cron_expression: crontab表达式
    :return: 如果时间落入crontab表达式内，返回True，否则返回False
    """
    base_time = datetime.now()

    return croniter.match(cron_expression, base_time)
