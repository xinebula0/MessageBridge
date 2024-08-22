from sqlalchemy import String, Integer, UUID, Text, PrimaryKeyConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import sessionmaker, scoped_session


# 创建数据库引擎
engine = create_engine('sqlite:///users.db', echo=True)

# 创建Session工厂
session_factory = sessionmaker(bind=engine)
SessionLocal = scoped_session(session_factory)


class Base(DeclarativeBase):
    pass


class RoutingRule(Base):
    __tablename__ = 'routing_rule'  # 定义表名称

    indicator: Mapped[str] = mapped_column(String)   # 消息内容类型
    source: Mapped = mapped_column(String)    # 消息来源
    destination: Mapped = mapped_column(String)  # 目标连接器

    __table_args__ = (
        PrimaryKeyConstraint('indicator', 'sourced'),
    )

    def __repr__(self):
        return (f"<RoutingRule(indicator='{self.indicator}', source='{self.source}', "
                f"destination_connector='{self.destination}')>")


class Message(Base):
    __tablename__ = 'message'  # 消息表

    id: Mapped = mapped_column(Integer, autoincrement=True, primary_key=True)  # 消息ID
    content: Mapped = mapped_column(Text)  # 消息内容
    receivers: Mapped = mapped_column(String(256))  # 接收者
    title: Mapped = mapped_column(String(256), nullable=False)  # 消息标题
    format: Mapped = mapped_column(String)  # 消息格式
    timestamp: Mapped = mapped_column(String)  # 时间戳
    sender: Mapped = mapped_column(String(256))  # 发送者
    status: Mapped = mapped_column(String(32))  # 消息状态
    uuid: Mapped = mapped_column(UUID)  # 消息唯一标识

    def __repr__(self):
        return (f"<Message(title='{self.title}', content='{self.content}', "
                f"receivers='{self.receivers}', sender='{self.sender}')>")