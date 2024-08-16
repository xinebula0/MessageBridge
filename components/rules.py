from abc import ABC, abstractmethod


class Message:
    def __init__(self, content, receivers, headers=None, format="JSON"):
        self.content = content
        self.receivers = receivers
        self.headers = headers if headers else {}
        self.format = format

    def transform(self, transformation_rule):
        """根据转换规则转换消息格式"""
        # 示例转换：将消息内容变为大写
        transformed_content = self.content.upper()
        return Message(content=transformed_content, headers=self.headers, format=self.format)


class TransformRule(ABC):
    @abstractmethod
    def transform(self, message):
        pass


class MailStrategy(TransformRule):
    def transform(self, message):
        message.content = f"Mail: {message.content}"
        return message
