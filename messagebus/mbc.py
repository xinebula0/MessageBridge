from messagebus.models import Message


class MessageBus:
    """ 消息总线
        管理所有连接器并处理消息的路由和传输。它可以注册连接器、接收消息、发送消息以及根据路由规则将消息路由到适当的目标。
        允许同步和异步方式调用
    """
    def __init__(self):
        self.connectors = []
        self.routing_rules = []

    def register_connector(self, connector):
        """注册一个新的连接器"""
        self.connectors.append(connector)

    def add_routing_rule(self, routing_rule):
        """添加一个路由规则"""
        self.routing_rules.append(routing_rule)

    def send_message(self, message):
        """将消息通过注册的连接器进行发送"""
        for connector in self.connectors:
            transformed_message = self._apply_transformations(message, connector)
            connector.send(transformed_message)

    def receive_message(self, connector_name):
        """从指定的连接器接收消息"""
        connector = self._find_connector_by_name(connector_name)
        if connector:
            message = connector.receive()
            self.route_message(message)
        else:
            raise ValueError(f"Connector {connector_name} not found")

    def route_message(self, message):
        """根据路由规则将消息发送到目标连接器"""
        for rule in self.routing_rules:
            if rule.is_match(message):
                destination_connector = self._find_connector_by_name(rule.destination_connector)
                if destination_connector:
                    transformed_message = self._apply_transformations(message, destination_connector)
                    destination_connector.send(transformed_message)

    def _apply_transformations(self, message, connector):
        """应用消息转换规则（如有必要）"""
        if hasattr(connector, 'transformation_rule'):
            return message.transform(connector.transformation_rule)
        return message

    def _find_connector_by_name(self, name):
        """根据名称查找连接器"""
        for connector in self.connectors:
            if connector.name == name:
                return connector
        return None


class Connector:
    def __init__(self, name, channel):
        self.name = name
        self.channel = channel
        self.transformation_rule = None

    def connect(self):
        """连接到消息中间件或平台"""
        print(f"{self.name} connected using {self.channel}")

    def disconnect(self):
        """断开连接"""
        print(f"{self.name} disconnected")

    def send(self, message):
        """发送消息"""
        print(f"Sending message via {self.name}: {message.content}")

    def receive(self):
        """接收消息"""
        message = Message(content="Hello from " + self.name)
        print(f"Received message: {message.content}")
        return message
