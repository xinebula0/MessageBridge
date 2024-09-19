from sqlalchemy import (String, Integer, Text, DateTime,
                        UniqueConstraint, PrimaryKeyConstraint,
                        Index, ForeignKey, Boolean)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from marshmallow import Schema, fields, post_load, pre_load
from datetime import datetime, timezone
from messagebus import db
from typing import Optional
from flask import g


class Subscription(db.Model):
    __tablename__ = 'subscription'  # 定义表名称

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, comment="订阅序号")
    sender: Mapped[str] = mapped_column(String(50), comment="消息发送者")
    recipient: Mapped[int] = mapped_column(ForeignKey("recipient.id"),
                                           nullable=False, comment="消息接收者")
    category: Mapped[str] = mapped_column(String(150), comment="消息类别")
    channel: Mapped[str] = mapped_column(String(50), comment="消息内容渠道")
    cronexpress: Mapped[str] = mapped_column(String(255), default="* * * * *", comment="定时发送表达式")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.now(),
                                                 comment="创建时间")

    __table_args__ = (
        UniqueConstraint('sender', 'recipient', 'category', 'channel'),
    )


class SubscriptionSchema(Schema):
    id = fields.Integer(dump_only=True)
    sender = fields.String(allow_none=False, required=True)
    recipient = fields.Integer(allow_none=False, required=True)
    category = fields.String(allow_none=False, required=True)
    channel = fields.String(allow_none=False, required=True)
    cronexpress = fields.String(allow_none=True, required=True)
    is_active = fields.Boolean(allow_none=True, required=True)
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S")

    @post_load
    def make_routing_rule(self, data, **kwargs):
        return Subscription(**data)

    @pre_load
    def check_crate_at(self, data, **kwargs):
        if not data.get("created_at"):
            data["created_at"] = datetime.now(timezone.utc)

        return data


class Message(db.Model):
    __tablename__ = 'message'  # 消息表

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, comment="消息ID")
    content: Mapped[str] = mapped_column(Text, comment="消息内容")
    title: Mapped[str] = mapped_column(String(150), nullable=False, comment="消息标题")
    category: Mapped[str] = mapped_column(String(150), nullable=False, comment="消息类别")
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.now(),
                                                 comment="创建时间")
    sent_at: Mapped[datetime] = mapped_column(nullable=True, comment="发送时间")
    sender: Mapped[str] = mapped_column(String(50), nullable=False, comment="发送者")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="消息状态")
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, comment="消息唯一uuid标识")


class MessageSchema(Schema):
    id = fields.Integer(dump_only=True)
    content = fields.String(required=True)
    title = fields.String(required=True)
    category = fields.String(allow_none=False, required=True)
    created_at = fields.DateTime(required=False, format="%Y-%m-%d %H:%M:%S")
    sent_at = fields.DateTime(allow_none=True, format="%Y-%m-%d %H:%M:%S")
    sender = fields.String(allow_none=False)
    status = fields.String(required=False)
    uuid = fields.String(required=False)

    @post_load
    def make_message(self, data, **kwargs):
        return Message(**data)

    @pre_load
    def format_message(self, data, **kwargs):
        if not data.get("status"):
            data["status"] = "created"

        if not data.get("uuid"):
            data["uuid"] = g.uuid

        return data


class Recipient(db.Model):
    __tablename__ = "recipient"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="个人姓名或群名称")
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="群标志")
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), comment="员工号，群可为空")
    monkeytalk: Mapped[Optional[str]] = mapped_column(String(50), comment="Monkey Talk的用户名")
    email: Mapped[Optional[str]] = mapped_column(String(254), comment="邮箱地址")
    bocsms: Mapped[Optional[str]] = mapped_column(String(50), comment="行信")
    last_updated: Mapped[datetime] = mapped_column(DateTime,
                                                   default=datetime.now(),
                                                   comment="最后更新时间")
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
    last_updated = fields.DateTime(allow_none=True, format="%Y-%m-%d %H:%M:%S")

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


class DeliveryLog(db.Model):
    __tablename__ = "delivery_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), comment="消息唯一uuid标识")
    task_id: Mapped[id] = mapped_column(String(36), comment="任务ID")
    recipient: Mapped[str] = mapped_column(String(100), nullable=False, comment="接收者name字段")
    employee_id: Mapped[str] = mapped_column(String(50), comment="员工号")
    channel: Mapped[str] = mapped_column(String(50), comment="发送渠道")
    status: Mapped[str] = mapped_column(String(32), comment="发送状态")
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.now(),
                                                 comment="更新时间")


class DeliveryLogSchema(Schema):
    id = fields.Integer(dump_only=True)
    uuid = fields.String(required=True, allow_none=False)
    task_id = fields.String(required=True, allow_none=False)
    recipient = fields.String(required=True, allow_none=False)
    employee_id = fields.String(allow_none=True)
    status = fields.String(required=True, allow_none=False)
    updated_at = fields.DateTime(allow_none=True, format="%Y-%m-%d %H:%M:%S")

    @post_load
    def make_deliverylog(self, data, **kwargs):
        return DeliveryLog(**data)


class Token(db.Model):
    __tablename__ = 'token'

    channel: Mapped[str] = mapped_column(String(50), primary_key=True, comment="渠道名称")
    access_token: Mapped[str] = mapped_column(Text, nullable=True, default=None, comment="访问token")
    token_type: Mapped[str] = mapped_column(String(50), nullable=True, default=None, comment="token类型")
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True, default=None, comment="更新token")
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None, comment="过期时间")


class TokenSchema(Schema):
    channel = fields.String(required=True, allow_none=False)
    access_token = fields.String(required=True, allow_none=False)
    token_type = fields.String(require=False, allow_none=True)
    refresh_token = fields.String(require=False, allow_none=True)
    expired_at = fields.DateTime(allow_none=True, format="%Y-%m-%d %H:%M:%S")

    @post_load
    def make_token(self, data, **kwargs):
        return Token(**data)
