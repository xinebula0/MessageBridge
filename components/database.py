from sqlalchemy import String, PrimaryKeyConstraint, create_engine
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
        return (f"<RoutingRule(keyword='{self.indicator}', source='{self.source}', "
                f"destination_connector='{self.destination}')>")


