from sqlalchemy import (String, Integer, Text, DateTime, JSON,
                        PrimaryKeyConstraint, Index, ForeignKey, Boolean)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from marshmallow import Schema, fields, post_load, pre_load
from datetime import datetime, timezone
import uuid
from messagebus import db
from typing import Optional


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


class Message(db.Model):
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


class Recipient(db.Model):
    __tablename__ = "recipient"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="个人姓名或群名称")
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="群标志")
    employee_id: Mapped[Optional[str]] = mapped_column(String(30), comment="员工号，群可为空")
    monkeytalk: Mapped[Optional[str]] = mapped_column(String(30), comment="Monkey Talk的用户名")
    email: Mapped[Optional[str]] = mapped_column(String(254), comment="邮箱地址")
    bocsms: Mapped[Optional[str]] = mapped_column(String(30), comment="行信")
    # 关系设置
    members: Mapped[list["RecipientGroup"]] = relationship(
        "RecipientGroup",
        foreign_keys="RecipientGroup.group",
        cascade="all, delete-orphan"
    )


class RecipientSchema(Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(allow_none=False)
    is_group = fields.Boolean(allow_none=False)
    employee_id = fields.String(allow_none=True)
    monkeytalk = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    bocsms = fields.String(allow_none=True)

    @post_load
    def make_recipient(self, data, **kwargs):
        return Recipient(**data)


class RecipientGroup(db.Model):
    __tablename__ = "recipient_group"

    group: Mapped[int] = mapped_column(ForeignKey("recipient.id", ondelete="CASCADE"),
                                       nullable=False)
    recipient: Mapped[int] = mapped_column(ForeignKey("recipient.id", ondelete="CASCADE"),
                                           nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        PrimaryKeyConstraint("group", "recipient"),
        Index("ix_group", "group")
    )


class RecipientGroupSchema(Schema):
    group = fields.Int(required=True, allow_none=False)
    recipient = fields.Int(required=True, allow_none=False)
    active = fields.Bool(require=True)

    @post_load
    def make_group(self, data, **kwargs):
        return RecipientGroup(**data)
