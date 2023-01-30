#!/bin/python3

## Event library and schemas

from datetime import datetime, timezone
from enum import Enum
from pprint import pformat
from socket import EWOULDBLOCK

from marshmallow import Schema, fields

class EventTypes(Enum):
    PABS_RAW_MESSAGE = "PabsRawMessage"
    ALBERT3_RAW_MESSAGE = "Albert3RawMessage"
    PABS_SIGNAL_MESSAGE = "PabsSignalMessage"
    PABS_UPDATE_MESSAGE = "PabsUpdateMessage"
    PABS_OTHER_MESSAGE = "PabsOtherMessage"
    PABS_SIGNAL_UPDATE = "PabsSignalUpdate"
    PING_MESSAGE = "PingMessage"
    BINANCE_TRADE_DATA_REQUEST = "BinanceTradeDataRequest"
    BINANCE_TRADE_DATA = "BinanceTradeData"
    AUDIT_EVENT = "AuditMessage"

# Base Event Container
class Event:
    def __init__(self, etype="NotSpecified", payload=dict()):
        self.etype = etype
        self.created_date = datetime.now(timezone.utc)
        self.payload = payload
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class EventSchema(Schema):
    etype = fields.Str(required=True, error_messages={"required": {"message": "etype is required"}})
    created_date = fields.DateTime(required=True)
    payload = fields.Dict(required=True)

## Raw Messages
class PabsRawMessageEvent():
    def __init__(self, raw_message):
        self.raw_message = raw_message
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class PabsRawMessageEventSchema(Schema):
    raw_message = fields.Str(required=True)

class Albert3RawMessageEvent():
    def __init__(self, raw_message):
        self.raw_message = raw_message
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class Albert3RawMessageEventSchema(Schema):
    raw_message = fields.Str(required=True)

## PABS Signal Event
class PabsSignalMessageEvent():
    def __init__(self, tracking_number, avg, date_inserted, entry_high, entry_low, pair, condensed_pair, trade_symbol, base_symbol, profit, risk, stoploss, targets):
        self.tracking_number = tracking_number
        self.avg = avg
        self.date_inserted = date_inserted
        self.entry_high = entry_high
        self.entry_low = entry_low
        self.pair = pair
        self.condensed_pair = condensed_pair
        self.trade_symbol = trade_symbol
        self.base_symbol = base_symbol
        self.profit = profit
        self.risk = risk
        self.stoploss = stoploss
        self.targets = targets
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class PabsSignalMessageEventSchema(Schema):
    avg = fields.Str(required=False)
    date_inserted = fields.Str(required=False)
    entry_high = fields.Float(required=True)
    entry_low = fields.Float(required=True)
    pair = fields.Str(required=True)
    condensed_pair = fields.Str(required=True)
    trade_symbol = fields.Str(required=True)
    base_symbol = fields.Str(required=True)
    profit = fields.Str(required=False)
    risk = fields.Int(required=False)
    stoploss = fields.Float(required=True)
    targets = fields.List(fields.Float(),required=True)
    tracking_number = fields.Str(required=False)

## PABS Update Event
class PabsUpdateMessageEvent():
    def __init__(self, tracking_number, date_inserted, update_type, status, error_information, next_stoploss_price,
    next_target_price, signal_decision, signal_entry_time, stoploss_decision, target_price,
    profit_percentage, pair, trade_symbol, base_symbol, condensed_pair):
        self.tracking_number = tracking_number
        self.date_inserted = date_inserted
        self.update_type = update_type
        self.status = status
        self.error_information = error_information
        self.next_stoploss_price = next_stoploss_price
        self.next_target_price = next_target_price
        self.signal_decision = signal_decision
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.target_price = target_price
        self.profit_percentage = profit_percentage
        self.pair = pair
        self.trade_symbol = trade_symbol
        self.base_symbol = base_symbol
        self.condensed_pair = condensed_pair
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class PabsUpdateMessageEventSchema(Schema):
    tracking_number = fields.Str(required=True)
    date_inserted = fields.Str(required=False)
    update_type = fields.Str(required=True)
    status = fields.Str(required=True)
    error_information = fields.Str(required=False)
    next_stoploss_price = fields.Float(required=False)
    next_target_price = fields.Float(required=False)
    signal_decision = fields.Str(required=True)
    signal_entry_time = fields.Str(required=False)
    stoploss_decision = fields.Str(required=False)
    target_price = fields.Float(required=False)
    profit_percentage = fields.Str(required=False)
    pair = fields.Str(required=False)
    trade_symbol = fields.Str(required=True)
    base_symbol = fields.Str(required=False)
    condensed_pair = fields.Str(required=False)

## PABS Signal Update Event
class PabsSignalUpdateEvent():
    def __init__(self, tracking_number, update_type, status, message, entry_price):
        self.tracking_number = tracking_number
        self.update_type = update_type
        self.date_inserted = datetime.now(timezone.utc)
        self.status = status
        self.message = message
        self.entry_price = entry_price
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class PabsSignalUpdateEventSchema(Schema):
    tracking_number = fields.Str(required=True)
    update_type = fields.Str(required=False)
    date_inserted = fields.Str(required=False)
    status = fields.Str(required=True)
    message = fields.Str(required=True)
    entry_price = fields.Str(required=False)

## Binance Trade Data Event
class BinanceTradeDataEventSchema(Schema):
    pair = fields.Str(required=True)
    request_type = fields.Str(required=True)
    trade_data = fields.Dict(required=True)

class BinanceTradeDataEvent():
    def __init__(self, pair, request_type, trade_data):
        self.pair = pair
        self.request_type = request_type
        self.trade_data = trade_data
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

## Test Events
class PingEvent():
    def __init__(self, msg):
        self.msg = "PING"
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class PingEventSchema(Schema):
    event_payload = fields.Str(required=False)
