from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from modules.database import Base
from pprint import pformat
from datetime import datetime
from modules.shared_libs import str_to_float

class WalletModel(Base):
    __tablename__ = 'binance_wallet'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    asset = Column(Text())
    free = Column(Float())
    locked = Column(Float())
    total = Column(Float())
    def __init__(self, asset, free, locked, total):
        self.asset = asset
        self.free = free
        self.locked = locked
        self.total = total
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class OrderModel(Base):
    __tablename__ = 'binance_order'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    tracking_number = Column(Text())
    market = Column(Text())
    order_type = Column(Text())
    qty = Column(Float())
    executed_qty = Column(Float())
    price = Column(Float())
    executed_price = Column(Float())
    status = Column(Text())
    error_information = Column(Text())
    message = Column(Text())
    order_data = Column(JSON())
    order_id = Column(Text())
    origin_process_id = Column(Text())
    def __init__(self, tracking_number, market, order_type, qty, executed_qty, price, executed_price, status, error_information, message, order_data, order_id, origin_process_id):
        self.tracking_number = tracking_number
        self.market = market
        self.order_type = order_type
        self.qty = qty
        self.executed_qty = executed_qty
        self.price = price
        self.executed_price = executed_price
        self.status = status
        self.error_information = error_information
        self.message = message
        self.order_data = order_data
        self.order_id = order_id
        self.origin_process_id = origin_process_id
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class Ticker:
    "CCXT Market Ticker"
    def __init__(self, success=False, symbol="NA", info="NA", timestamp="NA", datetime="NA", high="NA", low="NA", bid="NA", ask="NA", open="NA", close = "NA", last = "NA"):
        self.success = success
        self.symbol = symbol
        self.info = info
        self.timestamp = timestamp
        self.datetime = datetime
        self.high = str_to_float(high)
        self.low = str_to_float(low)
        self.bid = str_to_float(bid)
        self.ask = str_to_float(ask)
        self.open = str_to_float(open)
        self.close = str_to_float(close)
        self.last = str_to_float(last)
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)
    def default(self, o):
        return o.__dict__