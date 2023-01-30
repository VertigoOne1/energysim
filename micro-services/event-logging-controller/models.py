from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from modules.database import Base
from pprint import pformat
from datetime import datetime
from modules.shared_libs import str_to_float

class LoggingEventModel(Base):
    __tablename__ = 'global_logging_table'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    level = Column(Text())
    message = Column(JSON())
    def __init__(self, level, message):
        self.level = level
        self.message = message
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)