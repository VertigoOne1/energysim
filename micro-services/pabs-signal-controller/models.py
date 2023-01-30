from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from modules.database import Base
from pprint import pformat
from datetime import datetime

class SignalModel(Base):
    __tablename__ = 'PABS_Signals'
    id = Column(Integer, primary_key=True, autoincrement=True)
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    tracking_number = Column(Text())
    process_id = Column(Text())
    is_duplicate = Column(Text(), default='False')
    status = Column(Text())
    error_information = Column(Text())
    funding_allocated = Column(Float())
    qty_purchased = Column(Float())
    avg = Column(Float())
    entry_high = Column(Float())
    entry_low = Column(Float())
    entry_actual = Column(Float())
    pair = Column(Text())
    profit = Column(Text())
    risk = Column(Text())
    stoploss = Column(Float())
    targets = Column(JSON())
    targets_distribution = Column(JSON())
    qty_remaining = Column(Float())
    def __init__(self, tracking_number, process_id, is_duplicate, status, error_information, funding_allocated, qty_purchased, avg, entry_high, entry_low, entry_actual, pair, profit, risk, stoploss, targets, targets_distribution, qty_remaining):
        self.tracking_number = tracking_number
        self.process_id = process_id
        self.is_duplicate = is_duplicate
        self.status = status
        self.error_information = error_information
        self.funding_allocated = funding_allocated
        self.qty_purchased = qty_purchased
        self.avg = avg
        self.entry_high = entry_high
        self.entry_low = entry_low
        self.entry_actual = entry_actual
        self.pair = pair
        self.profit = profit
        self.risk = risk
        self.stoploss = stoploss
        self.targets = targets
        self.targets_distribution = targets_distribution
        self.qty_remaining = qty_remaining
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)

class UpdateModel(Base):
    __tablename__ = 'PABS_Updates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    linked_signal_id = Column(Integer)
    signal_process_id = Column(Text())
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    tracking_number = Column(Text())
    update_type = Column(Text())
    status = Column(Text())
    error_information = Column(Text())
    next_stoploss_price = Column(Float())
    next_target_price = Column(Float())
    signal_decision = Column(Text())
    signal_entry_time = Column(Text())
    stoploss_decision = Column(Text())
    target_price = Column(Float())
    signal_entry_price = Column(Float())
    actual_qty_sold = Column(Float())
    actual_price_sold = Column(Float())
    planned_qty = Column(Float())
    measured_profit_percentage = Column(Float())
    profit_percentage = Column(Text())
    pair = Column(Text())
    condensed_pair = Column(Text())
    trade_symbol = Column(Text())
    base_symbol = Column(Text())
    def __init__(self, linked_signal_id, signal_process_id, tracking_number, update_type, status, error_information, next_stoploss_price,
    next_target_price, signal_decision, stoploss_decision, signal_entry_time, target_price, signal_entry_price,
    actual_qty_sold, actual_price_sold, planned_qty, measured_profit_percentage, profit_percentage, pair, condensed_pair, trade_symbol, base_symbol):
        self.linked_signal_id = linked_signal_id
        self.signal_process_id = signal_process_id
        self.tracking_number = tracking_number
        self.update_type = update_type
        self.status = status
        self.error_information = error_information
        self.next_stoploss_price = next_stoploss_price
        self.next_target_price = next_target_price
        self.signal_decision = signal_decision
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.target_price = target_price
        self.signal_entry_price = signal_entry_price
        self.actual_qty_sold = actual_qty_sold
        self.actual_price_sold = actual_price_sold
        self.planned_qty = planned_qty
        self.measured_profit_percentage = measured_profit_percentage
        self.profit_percentage = profit_percentage
        self.pair = pair
        self.trade_symbol = trade_symbol
        self.base_symbol = base_symbol
        self.condensed_pair = condensed_pair
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)
    def __iter__(self):
        # some method to yield key/value tuples for dict(instance) conversion
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_sa_")}
        yield from data.items()


class PerformanceModel(Base):
    __tablename__ = 'PABS_Performance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    linked_signal_id = Column(Integer)
    signal_process_id = Column(Text())
    tracking_number = Column(Text())
    number_of_targets = Column(Integer())
    market = Column(Text())
    signal_completed = Column(Boolean())
    average_percent_gain = Column(Float())
    insert_date = Column(DateTime(), default=datetime.now)
    update_date = Column(DateTime(), onupdate=datetime.now)
    status = Column(Text())
    error_information = Column(Text())
    # Entry Cols
    funding_requested = Column(Float())
    funding_actioned = Column(Float())
    entry_price_requested = Column(Float())
    entry_price_actioned = Column(Float())
    entry_qty_requested = Column(Float())
    entry_qty_actioned = Column(Float())
    entry_completed = Column(Boolean())
    # Target1 Cols
    target1_price_requested = Column(Float())
    target1_price_actioned = Column(Float())
    target1_percent_allocation = Column(Float())
    target1_qty_allocated = Column(Float())
    target1_qty_actioned = Column(Float())
    target1_price_gain = Column(Float())
    target1_completed = Column(Boolean())
    # Target2 Cols
    target2_price_requested = Column(Float())
    target2_price_actioned = Column(Float())
    target2_percent_allocation = Column(Float())
    target2_qty_allocated = Column(Float())
    target2_qty_actioned = Column(Float())
    target2_price_gain = Column(Float())
    target2_completed = Column(Boolean())
    # Target3 Cols
    target3_price_requested = Column(Float())
    target3_price_actioned = Column(Float())
    target3_percent_allocation = Column(Float())
    target3_qty_allocated = Column(Float())
    target3_qty_actioned = Column(Float())
    target3_price_gain = Column(Float())
    target3_completed = Column(Boolean())
    # Target4 Cols
    target4_price_requested = Column(Float())
    target4_price_actioned = Column(Float())
    target4_percent_allocation = Column(Float())
    target4_qty_allocated = Column(Float())
    target4_qty_actioned = Column(Float())
    target4_price_gain = Column(Float())
    target4_completed = Column(Boolean())
    # Settlement Cols
    settlement_price_requested = Column(Float())
    settlement_price_actioned = Column(Float())
    settlement_percent_allocation = Column(Float())
    settlement_qty_allocated = Column(Float())
    settlement_qty_actioned = Column(Float())
    settlement_price_gain = Column(Float())
    settlement_completed = Column(Boolean())
    def __init__(self,
            linked_signal_id,
            signal_process_id,
            tracking_number,
            number_of_targets,
            market,
            signal_completed,
            average_percent_gain,
            status,
            error_information,
            funding_requested,
            funding_actioned,
            entry_price_requested,
            entry_price_actioned,
            entry_qty_requested,
            entry_qty_actioned,
            entry_completed,
            target1_price_requested,
            target1_price_actioned,
            target1_percent_allocation,
            target1_qty_allocated,
            target1_qty_actioned,
            target1_price_gain,
            target1_completed,
            target2_price_requested,
            target2_price_actioned,
            target2_percent_allocation,
            target2_qty_allocated,
            target2_qty_actioned,
            target2_price_gain,
            target2_completed,
            target3_price_requested,
            target3_price_actioned,
            target3_percent_allocation,
            target3_qty_allocated,
            target3_qty_actioned,
            target3_price_gain,
            target3_completed,
            target4_price_requested,
            target4_price_actioned,
            target4_percent_allocation,
            target4_qty_allocated,
            target4_qty_actioned,
            target4_price_gain,
            target4_completed,
            settlement_price_requested,
            settlement_price_actioned,
            settlement_percent_allocation,
            settlement_qty_allocated,
            settlement_qty_actioned,
            settlement_price_gain,
            settlement_completed):
        self.linked_signal_id = linked_signal_id
        self.signal_process_id = signal_process_id
        self.tracking_number = tracking_number
        self.number_of_targets = number_of_targets
        self.market = market
        self.signal_completed = signal_completed
        self.average_percent_gain = average_percent_gain
        self.status = status
        self.error_information = error_information
        self.funding_requested = funding_requested
        self.funding_actioned = funding_actioned
        self.entry_price_requested = entry_price_requested
        self.entry_price_actioned = entry_price_actioned
        self.entry_qty_requested = entry_qty_requested
        self.entry_qty_actioned = entry_qty_actioned
        self.entry_completed = entry_completed
        self.target1_price_requested = target1_price_requested
        self.target1_price_actioned = target1_price_actioned
        self.target1_percent_allocation = target1_percent_allocation
        self.target1_qty_allocated = target1_qty_allocated
        self.target1_qty_actioned = target1_qty_actioned
        self.target1_price_gain = target1_price_gain
        self.target1_completed = target1_completed
        self.target2_price_requested = target2_price_requested
        self.target2_price_actioned = target2_price_actioned
        self.target2_percent_allocation = target2_percent_allocation
        self.target2_qty_allocated = target2_qty_allocated
        self.target2_qty_actioned = target2_qty_actioned
        self.target2_price_gain = target2_price_gain
        self.target2_completed = target2_completed
        self.target3_price_requested = target3_price_requested
        self.target3_price_actioned = target3_price_actioned
        self.target3_percent_allocation = target3_percent_allocation
        self.target3_qty_allocated = target3_qty_allocated
        self.target3_qty_actioned = target3_qty_actioned
        self.target3_price_gain = target3_price_gain
        self.target3_completed = target3_completed
        self.target4_price_requested = target4_price_requested
        self.target4_price_actioned = target4_price_actioned
        self.target4_percent_allocation = target4_percent_allocation
        self.target4_qty_allocated = target4_qty_allocated
        self.target4_qty_actioned = target4_qty_actioned
        self.target4_price_gain = target4_price_gain
        self.target4_completed = target4_completed
        self.settlement_price_requested = settlement_price_requested
        self.settlement_price_actioned = settlement_price_actioned
        self.settlement_percent_allocation = settlement_percent_allocation
        self.settlement_qty_allocated = settlement_qty_allocated
        self.settlement_qty_actioned = settlement_qty_actioned
        self.settlement_price_gain = settlement_price_gain
        self.settlement_completed = settlement_completed
    def __repr__(self):
        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=2, width=1)