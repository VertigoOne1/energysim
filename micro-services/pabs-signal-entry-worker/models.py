from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from modules.database import Base
from pprint import pformat
from datetime import datetime

class EntryModel(Base):
    __tablename__ = 'PABS_Entry'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    tracking_number = Column(Text())
    pair = Column(Text())
    process_id = Column(Text())
    entry_high = Column(Float())
    entry_low = Column(Float())
    stoploss = Column(Float())
    entry_actual = Column(Float())
    status = Column(Text())
    error_information = Column(Text())
    last_price = Column(Float())
    entry_status = Column(Text())
    ws_status = Column(Text())
    feed_validated = Column(Boolean())
    def __init__(self, tracking_number, pair, process_id, entry_high, entry_low, stoploss, entry_actual, status, error_information, last_price, entry_status, ws_status, feed_validated):
        self.tracking_number = tracking_number
        self.pair = pair
        self.process_id = process_id
        self.entry_high = entry_high
        self.entry_low = entry_low
        self.stoploss = stoploss
        self.entry_actual = entry_actual
        self.status = status
        self.error_information = error_information
        self.last_price = last_price
        self.entry_status = entry_status
        self.ws_status = ws_status
        self.feed_validated = feed_validated
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)