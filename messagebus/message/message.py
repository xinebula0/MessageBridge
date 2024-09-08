from flask import jsonify, g
from flask.views import MethodView, request
from sqlalchemy import select
from messagebus.models import Subscription, MessageSchema, Recipient
from messagebus import db
import logging
from werkzeug.exceptions import BadRequest, NotImplemented, UnprocessableEntity
from croniter import croniter
from datetime import datetime

logger = logging.getLogger('MBus')


class MessageView(MethodView):
    def post(self):
        # 获取 JSON 数据
        data = request.get_json()

        if not data:
            raise BadRequest("No data provided")

        schema = MessageSchema()
        message = schema.load(data.get('Message'))
        message.uuid = g.uuid
        message.status = "created"
        db.session.add(message)
        db.session.commit()
        logger.info(f"【{message.title}】 from {message.sender} has been created.")

        stmt = select(Subscription).where(Subscription.sender == message.sender
                                          and
                                          Subscription.category == message.category
                                          and
                                          Subscription.is_active == True)
        subscriptions = db.session.execute(stmt).scalars().all()
        if not subscriptions:
            logger.error(f"{message.sender} with {message.category} has no subscription.")
            raise UnprocessableEntity(f"{message.sender} with {message.category} has no subscription.")

        wishlist = dict()
        for subscription in subscriptions:
            if not is_time_in_crontab(subscription.cronexpress):
                logger.info(f"【{message.title}】 "
                            f"from {message.sender} "
                            f"has been filtered by {subscription.recipient}")
                continue
            wishlist.setdefault(subscription.channel, []).append(subscription.recipient)

        # 获取各发送渠道所对应的所有订阅者
        recipients_in_channel = dict()
        for channel in wishlist:
            stmt = select(Recipient).where(Recipient.id.in_(wishlist[channel]))
            receivers = db.session.execute(stmt).scalars().all()
            for receiver in receivers:
                if receiver.is_group:
                    for member in receiver.members:
                        if member.active:
                            wishlist[channel].append(member.recipient)
            wishlist[channel] = list(set(wishlist[channel]))

            # 获取各channel的订阅者的对应的接收信息
            stmt = select(Recipient).where(Recipient.id.in_(wishlist[channel]))
            receivers = db.session.execute(stmt).scalars().all()
            for receiver in receivers:
                if not receiver.is_group:
                    if getattr(receiver, channel) is None:
                        logger.error(f"{receiver.name} has invalid {channel} channel.")
                        continue
                    recipients_in_channel.setdefault(channel, []).append(getattr(receiver, channel))

            g.mbus.send(channel, message, recipients_in_channel[channel])

        db.session.add(message)
        db.session.commit()

        return jsonify({"message": "Message sent"}), 200


def is_time_in_crontab(cron_expression):
    """
    判断给定的时间是否落入crontab表达式内

    :param cron_expression: crontab表达式
    :return: 如果时间落入crontab表达式内，返回True，否则返回False
    """
    base_time = datetime.now()
    cron = croniter(cron_expression, base_time)
    next_time = cron.get_next(datetime)
    prev_time = cron.get_prev(datetime)

    return prev_time <= base_time <= next_time

