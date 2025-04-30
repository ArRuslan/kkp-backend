class CustomMessageException(Exception):
    def __init__(self, messages: list[str] | str, status_code: int = 400):
        self.messages = messages if isinstance(messages, list) else [messages]
        self.status_code = status_code
