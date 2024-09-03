from sqlalchemy import String, Integer, Text, DateTime, JSON, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from marshmallow import Schema, fields, post_load, pre_load
from datetime import datetime, timezone
import uuid
from messagebus import db


class RoutingRule(db.Model):
    __tablename__ = 'routing_rule'  # 定义表名称

    channel: Mapped[str] = mapped_column(String, comment="消息内容类型")
    sender: Mapped[str] = mapped_column(String, comment="消息发送者")
    recipient: Mapped[str] = mapped_column(String, comment="消息接收者")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.now(timezone.utc),
                                                 comment="创建时间")

    __table_args__ = (
        PrimaryKeyConstraint('channel', 'sender', 'recipient'),
    )


class RoutingRuleSchema(Schema):
    sender = fields.String(required=True)
    channel = fields.String(required=True)
    recipient = fields.String(required=True)
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S")

    @post_load
    def make_routing_rule(self, data, **kwargs):
        return RoutingRule(**data)

    @pre_load
    def check_crate_at(self, data, **kwargs):
        if not data.get("created_at"):
            data["created_at"] = datetime.now(timezone.utc)

        return data


class Message(db.Mode):
    __tablename__ = 'message'  # 消息表

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, comment="消息ID")
    content: Mapped[str] = mapped_column(Text, comment="消息内容")
    recipients: Mapped[list] = mapped_column(JSON, comment="接收者")
    title: Mapped[str] = mapped_column(String, nullable=False, comment="消息标题")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc),comment="创建时间")
    sent_at: Mapped[datetime] = mapped_column(nullable=True, comment="发送时间")
    sender: Mapped[str] = mapped_column(String, comment="发送者")
    channels: Mapped[list] = mapped_column(JSON, comment="消息通道")
    status: Mapped[str] = mapped_column(String(32), comment="消息状态")
    uuid: Mapped[str] = mapped_column(String(36), comment="消息唯一uuid标识")


class MessageSchema(Schema):
    id = fields.Integer(dump_only=True)
    content = fields.String(required=True)
    recipients = fields.List(fields.Str(), required=True)
    title = fields.String(required=True)
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S")
    sent_at = fields.DateTime(allow_none=True, format="%Y-%m-%d %H:%M:%S")
    sender = fields.String()
    channels = fields.List(fields.Str(), required=True)
    status = fields.String()
    uuid = fields.String()

    @post_load
    def make_message(self, data, **kwargs):
        return Message(**data)

    @pre_load
    def format_message(self, data, **kwargs):
        if not data.get("status"):
            data["status"] = "created"

        if not data.get("uuid"):
            data["uuid"] = str(uuid.uuid4())

        if not data.get("recipients"):
            data["recipients"] = list()

        return data
