from abc import ABC, abstractmethod


class TransformRule(ABC):
    @abstractmethod
    def transform(self, message):
        pass


class MailStrategy(TransformRule):
    def transform(self, message):
        message.content = f"Mail: {message.content}"
        return message
