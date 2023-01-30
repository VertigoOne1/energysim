from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from modules.database import Base
from pprint import pformat
from datetime import datetime

class FileMessageModel(Base):
    __tablename__ = 'telegram_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    message = Column(Text())
    chat_id = Column(Text())
    topic_name = Column(Text())
    insert_date = Column(DateTime())

    def __init__(self, message, chat_id, topic_name, insert_date):
        self.chat_id = chat_id
        self.topic_name = topic_name
        self.message = message
        self.insert_date = insert_date

    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)