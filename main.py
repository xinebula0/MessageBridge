def main():
    # 创建消息总线
    bus = MessageBus()

    # 创建两个连接器
    connector_a = Connector(name="ConnectorA", protocol="AMQP")
    connector_b = Connector(name="ConnectorB", protocol="HTTP")

    # 注册连接器
    bus.register_connector(connector_a)
    bus.register_connector(connector_b)

    # 定义一个简单的路由规则：如果消息内容包含 "Hello"，则路由到 ConnectorB
    rule = RoutingRule(
        source_connector="ConnectorA",
        destination_connector="ConnectorB",
        condition=lambda msg: "Hello" in msg.content
    )

    # 添加路由规则
    bus.add_routing_rule(rule)

    # 同步发送消息
    bus.send_message(Message(content="Hello, this is a test message!"), "ConnectorA")

    # 异步发送消息
    bus.send_message(Message(content="Hello, this is an async test!"), "ConnectorA", async_mode=True)

    # 同步接收消息
    bus.receive_message("ConnectorA")

    # 异步接收消息
    bus.receive_message("ConnectorA", async_mode=True)

# 运行主函数
main()
