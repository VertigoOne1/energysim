from enum import auto
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from modules.database import Base
from pprint import pformat
from datetime import datetime

class ActiveFeedsModel(Base):
    __tablename__ = 'binance_active_feeds'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    tracking_number = Column(Text())
    status = Column(Text())
    error_information = Column(Text())
    pair = Column(Text())
    type = Column(Text())
    detail = Column(JSON())
    def __init__(self, tracking_number, status, error_information, pair, type, detail):
        self.tracking_number = tracking_number
        self.status = status
        self.error_information = error_information
        self.pair = pair
        self.type = type
        self.detail = detail
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)