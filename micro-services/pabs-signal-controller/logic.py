#!/bin/python3

from dis import dis
import sys, traceback
from typing import final
sys.path.append(r'./modules')

import requests, socket, time, re, json, ast
from envyaml import EnvYAML
import os, fnmatch, math
from pprint import pformat
from random import randint
import modules.eventbus as eventbus, modules.events as events, apicontroller as apicontroller

from modules.database import db_session
from modules.logger import setup_custom_logger
import models, metrics
import modules.bpm as bpm, modules.shared_libs as shared_libs

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

BROKER_URL = config['kafka']['broker_url']
TOPIC_PREFIX = config['kafka']['kafka_topic_prefix']

PING_MINIMUM_WAIT = 1

def decode_new_signal_event(data):
    from marshmallow import ValidationError
    event_schema = events.EventSchema()
    event = {}
    signal = ""
    try:
        event = event_schema.loads(data)
    except ValidationError as err:
        logger.error(err.messages)
        logger.error(err.valid_data)
        logger.error("Malformed event skipped")
        metrics.p_event_validation_errors.inc()
    if event:
        logger.trace(pformat(event))
        metrics.p_events_valid.inc()
        try:
            logger.info("Received new signal event")
            if event["etype"] == events.EventTypes.PABS_SIGNAL_MESSAGE.value:
                signal_schema = events.PabsSignalMessageEventSchema()
                try:
                    signal = signal_schema.loads(json.dumps(event["payload"]))
                    logger.debug(pformat(signal))
                    status = process_new_signal_event(signal)
                    if status['success']:
                        return status
                    else:
                        return dict(success = False, error = status)
                except Exception:
                    logger.error(traceback.format_exc())
                    logger.error("Issue loding signal")
                    return {}
        except Exception:
            logger.error(traceback.format_exc())
            logger.error("Issue loading signal")
            return {}

def consume(topic, group):
    from kafka import KafkaConsumer
    from marshmallow import ValidationError
    consumer = KafkaConsumer(bootstrap_servers=BROKER_URL,group_id=group,
                            auto_offset_reset=config["kafka"]["auto_offset_reset"], enable_auto_commit=True,
                            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
    consumer.subscribe(topic)
    for message in consumer:
        logger.debug("Received message from Kafka")
        data = message.value
        metrics.p_events_consumed.inc()
        logger.trace(pformat(data))
        event_schema = events.EventSchema()
        event = {}
        signal = ""
        try:
            event = event_schema.loads(data)
        except ValidationError as err:
            logger.error(err.messages)
            logger.error(err.valid_data)
            logger.error("Malformed event skipped")
            metrics.p_event_validation_errors.inc()
        if event:
            logger.trace(pformat(event))
            metrics.p_events_valid.inc()
            try:
                logger.info("Received Event from Kafka")
                # if event["etype"] == events.EventTypes.PABS_SIGNAL_MESSAGE.value:
                #     signal_schema = events.PabsSignalMessageEventSchema()
                #     try:
                #         signal = signal_schema.loads(json.dumps(event["payload"]))
                #         logger.debug(pformat(signal))
                #         status = process_new_signal_event(signal)
                #         if status['success']:
                #             logger.debug("Signal processed")
                #             bpm.start_process("SignalProcessing", {"signal_id": status['id'], "is_duplicate":status['is_duplicate']}, business_key=status['tracking_number'])
                #         else:
                #             logger.debug(f"Signal ignored, duplicate or error - {status}")
                #     except ValidationError as err:
                #         logger.error(err.messages)
                #         logger.error(err.valid_data)
                #         logger.warn("Malformed payload skipped")
                #         metrics.p_payload_validation_errors.inc()
                if event["etype"] == events.EventTypes.PABS_SIGNAL_UPDATE.value:
                    update_schema = events.PabsSignalUpdateEventSchema()
                    try:
                        signal_update = update_schema.loads(json.dumps(event["payload"]))
                        logger.trace(pformat(signal_update))
                        # if process_signal_update_event(signal_update):
                        #     logger.trace("Signal update processed")
                        # else:
                        #     logger.error("Error processing signal update")
                        #     logger.error(pformat(signal_update))
                    except ValidationError as err:
                        logger.error(err.messages)
                        logger.error(err.valid_data)
                        logger.error("Malformed payload skipped")
                        metrics.p_payload_validation_errors.inc()
                elif event["etype"] == events.EventTypes.BINANCE_TRADE_DATA_REQUEST.value:
                    logger.trace("Ignoring trade data request event etype")
                elif event["etype"] == events.EventTypes.BINANCE_TRADE_DATA.value:
                    logger.trace("Processing trade data event etype")
                else:
                    logger.trace("Event etype not handled by this service")
            except KeyError as err:
                logger.error(pformat(err))

def process_new_signal_event(signal):
    newSig = True
    check_existing = count_signals_by_tracking_number(signal['tracking_number'])
    if check_existing['count'] > 0:
        newSig = False
    if newSig:
        logger.info(f"Empty DB, or new signal, inserting new signal - {signal['tracking_number']}")
        result = store_signal(signal, is_duplicatep=False)
        if result['success']:
            return dict(success = True, tracking_number = signal['tracking_number'], id = result['id'], is_duplicate = False )
        else:
            return dict(success = False, error = result )
    else:
        logger.debug("Signal seen before, do we allow it?")
        if config["general"]["allow_duplicate_signals"]:
            logger.warn("Duplicate signals are allowed")
            result = store_signal(signal, is_duplicatep = True)
            if result['success']:
                return dict(success = True, tracking_number = signal['tracking_number'], id = result['id'], is_duplicate = True)
            else:
                return dict(success = False, error = result )
        else:
            logger.warn("Duplicate signals are not allowed, not continuing")
            return dict(success = False, error = "Signal seen before" )

def calculate_order_qty(price, funding_amount, min_lot_size):
    logger.info("You need to do the round up to the nearest MIN_NOTATIONAL calculation PLEASE")
    try:
        qty = float(funding_amount) / float(price)
        qty_result = shared_libs.qty_mod(qty, min_lot_size)
        logger.debug(f"{qty_result}")
        if qty_result['success']:
            logger.debug(f"Qty to order - {qty_result['qty']:.8f}")
            return float(qty_result['qty'])
        else:
            logger.error("Could not complete qty_mod calc successfully")
            return float(0.0)
    except:
        logger.error(f"could not calculate buy order qty - price - {price:.8f} - funding - {funding_amount:.8f}")
        return float(0.0)

def place_market_buy_order(tracking_number, market, price, funding, origin_process_id, min_lot_size):
    import requests
    import json
    logger.debug("entered place_market_buy_order")
    order_request = {}
    order_request['tracking_number'] = tracking_number
    order_request['market'] = market
    order_request['qty'] = calculate_order_qty(price, funding, min_lot_size)
    order_request['order_type'] = "spot-market-buy"
    order_request['price'] = price
    order_request['origin_process_id'] = origin_process_id
    logger.debug(pformat(order_request))
    try:
        res = requests.post(f"{config['envoy']['host']}/binance-rest-controller/market_buy_order", json = order_request)
        response = json.loads(res.text)
        logger.debug(response)
        return response
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue with response from binance rest controller")
        return {}

def place_market_sell_order(tracking_number, update_type, market, price, qty):
    import requests
    import json
    order_request = {}
    order_request['tracking_number'] = tracking_number
    order_request['update_type'] = update_type
    order_request['order_type'] = "spot-market-sell"
    order_request['market'] = market
    order_request['qty'] = qty
    order_request['price'] = price
    logger.debug(pformat(order_request))
    try:
        res = requests.post(f"{config['envoy']['host']}/binance-rest-controller/market_sell_order", json = order_request)
        response = json.loads(res.text)
        logger.debug(response)
        return response
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue with response from binance rest controller")
        return {}

def place_limit_order(tracking_number, market, qty, price):
    logger.debug("Not implemented for PABS yet")
    return False

## Fetch market data from binance controller
def fetch_market(symbol):
    import requests
    import json
    try:
        res = requests.get(f"{config['envoy']['host']}/binance-rest-controller/market?market={symbol}")
        logger.debug(res)
        response = json.loads(res.text)
        logger.debug(response)
        return dict(success = True, market = response)
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue with response from binance controller")
        return dict(success = False, id = 0, market = {}, error = traceback.format_exc())

def validate_market(symbol):
    ticker = fetch_market_ticker(symbol)
    if ticker['success']:
        logger.debug("Ticker sucessfully retrieved")
        logger.debug(f"{ticker['ticker']}")
        return ticker
    else:
        return dict(success = False, ticker = {}, error = traceback.format_exc())

## Fetch ticker data from binance controller
def fetch_market_ticker(symbol):
    import requests
    import json
    try:
        res = requests.get(f"{config['envoy']['host']}/binance-rest-controller/ticker?market={symbol}")
        response = json.loads(res.text)
        logger.trace(response)
        return dict(success = True, ticker = response)
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue with response from binance controller")
        return dict(success = False, id = 0, error = traceback.format_exc())

def validate_market(symbol):
    ticker = fetch_market_ticker(symbol)
    if ticker['success']:
        logger.debug("Ticker sucessfully retrieved")
        logger.debug(f"{ticker['ticker']}")
        return ticker
    else:
        return dict(success = False, ticker = {}, error = traceback.format_exc())

## Checks if were in sandbox mode or not, this affects the available markets and validation
def fetch_binance_controller_mode():
    import requests
    import json
    try:
        res = requests.get(f"{config['envoy']['host']}/binance-rest-controller/operatingMode")
        response = json.loads(res.text)
        logger.trace(response)
        return response
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue with response from binance controller")
        return {}

## PABS denominators might not be standard values, like 659, versus ticker as 0.00000659, this gets them to match the last ticker
def check_fix_price_denominator(ticker, signal):
    fixed_pricing = {}
    fixed_pricing["targets"] = []
    logger.debug(ticker)
    if ticker and signal:
        denom_ask = math.floor(math.log10(float(ticker['ask'])))
        denom_entry_high = math.floor(math.log10(float(signal['entry_high'])))
        denom_entry_low = math.floor(math.log10(float(signal['entry_low'])))
        logger.trace(f"Denominator - ask - {denom_ask:.8f}")
        logger.trace(f"Denominator - denom_entry_high - {denom_entry_high:.8f}")
        logger.trace(f"Denominator - denom_entry_low - {denom_entry_low:.8f}")
        if denom_entry_high == denom_entry_low:
            logger.trace("Fairly safe to convert denomination to the market rate (but we'll check it again)")
            logger.trace(pformat(signal))
            if (1 - denom_ask) < (1 - denom_entry_low):
                correction = (10 ** ((1 - denom_entry_high) - (1 - denom_ask)))
                logger.trace(f"Old Low Entry - {signal['entry_low']:.8f}")
                fixed_pricing["entry_high"] = signal['entry_high'] * correction
                fixed_pricing["entry_low"] = signal['entry_low'] * correction
                fixed_pricing["stoploss"] = signal['stoploss'] * correction
                logger.trace(f"New low Entry - {signal['entry_low']:.8f}")
                for i in range(len(signal['targets'])):
                    logger.trace(f"Target - {i} - {signal['targets'][i]:.8f}")
                    fixed_pricing["targets"].append(signal['targets'][i] * correction)
                logger.trace(pformat(fixed_pricing))
                logger.warn("Denominators fixed, lets continue")
                fixed_pricing["success"] = True
                fixed_pricing["error"] = ""
                logger.warn(pformat(fixed_pricing))
                return fixed_pricing
            elif (1 - denom_ask) > (1 - denom_entry_low):
                logger.error(pformat(signal))
                logger.error("wow ok, this i have to see, the denominator is the OTHER way around")
                fixed_pricing["success"] = False
                fixed_pricing["error"] = "denomination mismatch is wrong way around"
                logger.error(pformat(fixed_pricing))
                return fixed_pricing
            elif (1 - denom_ask) == (1 - denom_entry_low):
                logger.trace(pformat(signal))
                logger.debug("Denominators matched, lets continue")
                fixed_pricing["entry_high"] = signal['entry_high']
                fixed_pricing["entry_low"] = signal['entry_low']
                fixed_pricing["stoploss"] = signal['stoploss']
                fixed_pricing["success"] = True
                fixed_pricing["error"] = ""
                for i in range(len(signal['targets'])):
                    logger.debug(f"Target - {i} - {signal['targets'][i]}")
                    fixed_pricing["targets"].append(signal['targets'][i])
                logger.trace(pformat(fixed_pricing))
                return fixed_pricing
            else:
                logger.error("This i have to see, the donimators are not anything known to science")
                fixed_pricing["success"] = False
                fixed_pricing["error"] = "denomination failed math principles"
                logger.error(signal)
                logger.error(fixed_pricing)
                return fixed_pricing
        else:
            logger.warn("Unsafe situation to adjust, entry-high and entry-low are using different denominators, they might be ok, so continuing to checks")
            fixed_pricing["success"] = True
            fixed_pricing["entry_high"] = signal['entry_high']
            fixed_pricing["entry_low"] = signal['entry_low']
            fixed_pricing["stoploss"] = signal['stoploss']
            for i in range(len(signal['targets'])):
                logger.debug(f"Target - {i} - {signal['targets'][i]}")
                fixed_pricing["targets"].append(signal['targets'][i])
            fixed_pricing["error"] = "different denominations, cannot adjust, should be fine"
            return fixed_pricing
    else:
        fixed_pricing["success"] = False
        fixed_pricing["error"] = "missing parameter data"
        logger.error(pformat(fixed_pricing))
        return fixed_pricing

## This checks that the signal data is matching to within a range for the market data, not to high, low, makes sense to trade with as the market can change quickly.
def check_signal_vs_market(ticker, signal):
    validation = {}
    if config['validation']['mock']:
        logger.info('MOCK IS ACTIVE!')
        logger.info('MOCK IS ACTIVE!')
        logger.info('MOCK IS ACTIVE!')
    logger.debug(ticker)
    # Are the targets more than 3 times bigger or smaller than the current bid?
    validation["stage"] = "target checks"
    for target in signal['targets']:
        logger.trace(f"Target - {target}")
        try:
            target_variance = float(target) / float(ticker['bid'])
        except Exception:
            logger.error(traceback.format_exc())
            if config['validation']['mock']:
                logger.warn("Possible division by zero on test net, ignoring")
                target_variance = 1.1
            else:
                logger.error("Possible division by zero")
                validation["error"] = "division by zero - " + pformat(target) + " - " + pformat(ticker['bid'])
                validation["success"] = False
        if target_variance > 2.6 or target_variance <= 1.01:
            logger.error(f"Suspect target variance detected - {target_variance}")
            validation["error"] = "Suspect target variance detected"
            if config['validation']['mock']:
                validation["success"] = True
            else:
                validation["success"] = False
            return validation
    # Is the stop loss above the bid
    validation["stage"] = "stoploss checks"
    if float(signal['stoploss']) > float(ticker['bid']):
        logger.error(f"Suspect stoploss - {signal['stoploss']:.8f} variance detected, higher than bid - {ticker['bid']:.8f} pricing")
        validation["error"] = f"Suspect stop loss detected, higher than current bid - {signal['stoploss']:.8f}"
        if config['validation']['mock']:
            logger.warn("Ignoring due to sandbox")
            validation["error"] = "Mocking mode suspect stoploss ignored"
            validation["success"] = True
        else:
            validation["error"] = f"Suspect stoploss - {signal['stoploss']:.8f} variance detected, higher than bid - {ticker['bid']:.8f} pricing"
            logger.error(validation["error"])
            if config['validation']['mock']:
                validation["success"] = True
            else:
                validation["success"] = False
            return validation
    # Is the scalp zone making sense
    validation["stage"] = "entry point checks"
    entry_high_var = float(signal['entry_high']) / float(ticker['bid'])
    entry_low_var = float(signal['entry_low']) / float(ticker['bid'])
    if entry_high_var >= 1.15 or entry_low_var >= 1.1:
        logger.warn(f"Suspect high entry_price variance - {entry_high_var} - {entry_low_var}")
        validation["error"] = "Suspect high entry_price variance"
        if config['validation']['mock']:
            validation["success"] = True
        else:
            validation["success"] = False
            logger.error(validation["error"])
        return validation
    elif entry_high_var <= 0.6 or entry_low_var <= 0.6:
        logger.warn(f"Suspect low entry_price variance - {entry_high_var} - {entry_low_var}")
        validation["error"] = "Suspect low entry_price variance"
        if config['validation']['mock']:
            validation["success"] = True
        else:
            validation["success"] = False
            logger.error(validation["error"])
        return validation
    if float(signal['entry_low']) >= float(ticker['ask']) or float(signal['entry_high']) >= float(ticker['ask']):
        logger.debug(f"Ask - {ticker['ask']}")
        logger.debug(f"entry_low - {signal['entry_low']}")
        logger.debug(f"entry_high - {signal['entry_high']}")
        if config["validation"]["allow_ask_price_in_entry_zone"]:
            logger.warn("----")
            logger.warn("current configuration allows a real time ask price within the entry zone")
            logger.warn("Meaning a buy will be placed immediately")
            logger.warn("THIS IS DANGEROUS")
            logger.warn("----")
            logger.warn(f"Ask - {ticker['ask']:.8f}")
            logger.warn(f"Bid - {ticker['ask']:.8f}")
            logger.warn(f"entry_low - {signal['entry_low']:.8f}")
            logger.warn(f"entry_high - {signal['entry_low']:.8f}")
            validation["error"] = ""
            validation["success"] = True
            return validation
        else:
            validation["error"] = f"Entry - {signal['entry_high']:.8f} order is above current ask {ticker['bid']:.8f}, order will execute immediately"
            if config['validation']['mock']:
                validation["success"] = True
            else:
                validation["success"] = False
                logger.error(validation["error"])
            return validation
    if float(signal['risk']) >= float(config["validation"]["maximum_risk_tolerance"]):
        validation["error"] = f"risk - {signal['risk']} above current risk threshold - {config['validation']['maximum_risk_tolerance']}"
        if config['validation']['mock']:
            logger.warn(f"Signal is higher than configured risk tolerance - {config['validation']['maximum_risk_tolerance']}")
            validation["success"] = True
        else:
            validation["success"] = False
        return validation
    else:
        logger.trace(f"Ask - {ticker['ask']:.8f}")
        logger.trace(f"Bid - {ticker['ask']:.8f}")
        logger.trace(f"entry_low - {signal['entry_low']:.8f}")
        logger.trace(f"entry_high - {signal['entry_low']:.8f}")
        validation["error"] = ""
        validation["success"] = True
        logger.debug(pformat(validation))
        return validation

def fetch_matched_signal(tracking_number):
    from sqlalchemy import select
    session = db_session()
    if tracking_number:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.tracking_number == tracking_number)
            result = shared_libs.row2dict(session.execute(statement).scalars().last())
            if result:
                logger.trace(f"Got - {result}")
                return shared_libs.floaty_sig(result)
            else:
                logger.error(f"Signal - {tracking_number} - not found")
                return dict(success = False, id = 0, error = f"Signal - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, tracking_number = tracking_number, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No tracking_number to fetch")
        return dict(success = False, tracking_number = tracking_number, error = "No ID to fetch")

def market_data_request_event(pair, type, interval):
    logger.debug(f"Requesting signal market data - {pair} - Request Type - {type} Interval - {interval}")
    do_emit = True
    try:
        if do_emit:
            event_payload = events.BinanceTradeDataRequestEvent(pair, type, interval)
            logger.trace("Constructed Event Payload - ")
            logger.trace(pformat(event_payload))
            payload_schema = events.BinanceTradeDataRequestEventSchema()
            payload = payload_schema.dump(event_payload)
            logger.trace(pformat(payload))
            event_base = events.Event(events.EventTypes.BINANCE_TRADE_DATA_REQUEST.value, payload)
            base_schema = events.EventSchema()
            logger.trace("Constructed Event Package - ")
            logger.trace(pformat(event_base))
            logger.trace(pformat(base_schema))
            eventbus.emit(TOPIC_PREFIX+config['kafka']["binance_topic"], base_schema.dumps(event_base))
            logger.trace("Increment counter")
            metrics.p_events_emit_success.inc()
            return True
        else:
            metrics.p_events_emit_failed.inc()
            logger.error("emitting of events are disabled in code")
            return False
            # Build failed event log here
    except Exception:
        logger.error("Issue with event emit for market data request")
        logger.error(traceback.format_exc())

def update_signal_status(idp, tracking_number, status, error_information=""):
    logger.debug(f"Update signal - {tracking_number} status in db - {status} - {error_information}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if status:
                    result.status = status
                if error_information:
                    result.error_information = error_information
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Signal - {idp} - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception updating signal information")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_denomination(idp, tracking_number, pricing):
    logger.debug(f"Update signal - {tracking_number} denomination in db - {pricing}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if pricing:
                    result.stoploss = pricing["stoploss"]
                    result.entry_high = pricing["entry_high"]
                    result.entry_low = pricing["entry_low"]
                    result.targets = pricing["targets"]
                    session.add(result)
                    session.commit()
                    return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Signal - {idp} - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_funding(idp, tracking_number, funding_validation):
    logger.debug(f"Update signal - {tracking_number} funding information in db - {funding_validation['decision']['base_symbol_funds_allocated']}")
    session = db_session()
    from sqlalchemy import select
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if funding_validation:
                    result.funding_allocated = funding_validation["decision"]["base_symbol_funds_allocated"]
                    session.add(result)
                    session.commit()
                    return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Signal - {idp} - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_process_id(idp, tracking_number, process_id):
    logger.debug(f"Update signal - {tracking_number} process id {process_id}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if process_id:
                    result.process_id = process_id
                    session.add(result)
                    session.commit()
                    return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Signal - {idp} - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_executed_qty(idp, tracking_number, qty_purchased, entry_actual):
    logger.trace(f"Update signal - {tracking_number} qty_purchased information in db - {qty_purchased}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if qty_purchased:
                    result.qty_purchased = qty_purchased
                if entry_actual:
                    result.entry_actual = entry_actual
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Signal - {idp} - {tracking_number} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_target_distribution(idp, dist):
    logger.trace(f"Update update")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if dist and len(dist) > 0:
                    result.targets_distribution = json.dumps(dist)
                else:
                    logger.error("Empty distribution")
                    return dict(success = False, id = idp, error = "Empty distribution")
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Update - {idp} - not found")
                return dict(success = False, id = idp, error = f"Update - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_signal_qty_remaining(idp, qty):
    logger.trace(f"Update signal quantity remaining - {qty}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if qty:
                    result.qty_remaining = float(qty)
                else:
                    logger.error("no qty")
                    return dict(success = False, id = idp, error = "no qty")
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Signal - {idp} - not found")
                return dict(success = False, id = idp, error = f"Update - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_update_executed_info(idp, update_pack):
    logger.trace(f"Update update")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.UpdateModel).filter(models.UpdateModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if update_pack:
                    result.actual_qty_sold = update_pack['actual_qty_sold']
                    result.actual_price_sold = update_pack['actual_price_sold']
                    result.status = update_pack['status']
                    result.error_information = update_pack['error_information']
                else:
                    logger.error("Empty data pack")
                    return dict(success = False, id = idp, error = "Empty data pack")
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Update - {idp} - not found")
                return dict(success = False, id = idp, error = f"Update - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def funding_calc(funding_calc_model, base_funds, base_symbol):
    logger.debug(f"Funding Calculation - {funding_calc_model}")
    allowance = {}
    allowance["success"] = False
    allowance["base_symbol_funds_allocated"] = 0.0
    allowance["usd_allocation"] = 0.0
    allowance["funding_model"] = 0.0
    allowance["error"] = ""
    if funding_calc_model == "dollar_based":
        try:
            base_symbol_market_value = fetch_market_ticker(base_symbol.lower() + "usdt")
            logger.debug(f"{base_symbol} - USDT - {base_symbol_market_value}")
            allowed_funds = float(config["funding"]["basic_dollar_based"])
            last_close = float(base_symbol_market_value['ticker']["close"])
            allowed_base_fund = allowed_funds / last_close
            if base_funds > allowed_base_fund:
                logger.debug("Enough funds available")
                allowance["success"] = True
                allowance["base_symbol_funds_allocated"] = allowed_base_fund
                allowance["usd_allocation"] = allowed_funds
                allowance["funding_model"] = funding_calc_model
                allowance["available_balance"] = base_funds
                allowance["error"] = ""
                logger.debug(allowance)
            else:
                logger.error("Insufficient funds, not funding")
                allowance["success"] = False
                allowance["base_symbol_funds_allocated"] = allowed_base_fund
                allowance["usd_allocation"] = allowed_funds
                allowance["funding_model"] = funding_calc_model
                allowance["available_balance"] = base_funds
                allowance["error"] = "Insuffient Funds"
                logger.debug(allowance)
        except Exception:
            logger.error("Issue with funding calculation")
            logger.error(traceback.format_exc())
            allowance["success"] = False
            allowance["base_symbol_funds_allocated"] = 0.0
            allowance["usd_allocation"] = 0.0
            allowance["funding_model"] = 0.0
            allowance["available_balance"] = 0.0
            allowance["error"] = "Exception, likely with ticker information"
            logger.error(allowance)
            return allowance
    else:
        logger.error("Not funding")
        allowance["success"] = False
        allowance["base_symbol_funds_allocated"] = 0.0
        allowance["usd_allocation"] = 0.0
        allowance["funding_model"] = funding_calc_model
        allowance["available_balance"] = base_funds
        allowance["error"] = "Funding model not found"
        logger.error(allowance)
    return allowance

def process_signal_funding(idp):
    logger.trace("Check for funding work")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                try:
                    funding_validation = check_signal_funding(result.tracking_number, result.pair)
                    if funding_validation and funding_validation["success"]:
                        update_signal_funding(result.id, result.tracking_number, funding_validation)
                    else:
                        logger.error("Signal failed funding")
                except Exception:
                    logger.error(traceback.format_exc())
                    logger.error("Exception dealing with market checks")
            else:
                logger.trace("signal not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.trace("No signals in table")

def fetch_min_lot_size(market_info):
    min_qty = 1
    matched = False
    for f in market_info['market']['info']['filters']:
        if f['filterType'] == 'LOT_SIZE':
            min_qty = f['minQty']
            logger.debug(f"Minimum Order Qty: {min_qty}")
            matched = True
            return min_qty
    if not matched:
        logger.error("Could not find minimum lot size")
        return min_qty

# 'info': {'allowTrailingStop': False,
#          'baseAsset': 'DOGE',
#          'baseAssetPrecision': '8',
#          'baseCommissionPrecision': '8',
#          'filters': [{'filterType': 'PRICE_FILTER',
#                       'maxPrice': '1000.00000000',
#                       'minPrice': '0.00000001',
#                       'tickSize': '0.00000001'},
#                      {'avgPriceMins': '5',
#                       'filterType': 'PERCENT_PRICE',
#                       'multiplierDown': '0.2',
#                       'multiplierUp': '5'},
#                      {'filterType': 'LOT_SIZE',
#                       'maxQty': '90000000.00000000',
#                       'minQty': '1.00000000',
#                       'stepSize': '1.00000000'},
#                      {'applyToMarket': True,
#                       'avgPriceMins': '5',
#                       'filterType': 'MIN_NOTIONAL',
#                       'minNotional': '0.00010000'},
#                      {'filterType': 'ICEBERG_PARTS', 'limit': '10'},
#                      {'filterType': 'MARKET_LOT_SIZE',
#                       'maxQty': '10380285.37430555',
#                       'minQty': '0.00000000',
#                       'stepSize': '0.00000000'},
#                      {'filterType': 'TRAILING_DELTA',
#                       'maxTrailingAboveDelta': '2000',
#                       'maxTrailingBelowDelta': '2000',
#                       'minTrailingAboveDelta': '10',
#                       'minTrailingBelowDelta': '10'},
#                      {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': '200'},
#                      {'filterType': 'MAX_NUM_ALGO_ORDERS',
#                       'maxNumAlgoOrders': '5'}],

def calc_target_sell_ability(qty, ask, min_notional):
    result = {}
    order_value = qty * ask
    logger.debug(f"Order value - {order_value:.8f} - required {min_notional:.8f}")
    if float(order_value) < float(min_notional):
        logger.error("This order value will fail placement")
        result['success'] = False
        return result
    else:
        result['success'] = True
        return result

def process_target_funding(idp, purchased_qty, market_info, ticker):
    logger.debug("Calculate Target Sell Distribution")
    logger.debug(f"Available QTY: {purchased_qty}")
    logger.debug(f"Market Info:")
    logger.debug(pformat(market_info))
    logger.debug("Returned Limits - ")
    logger.debug(pformat(market_info['market']['limits']))
    min_notional = float(market_info['market']['limits']['cost']['min'])
    ask = float(ticker['ticker']['ask'])
    min_lot_size = float(fetch_min_lot_size(market_info))
    logger.debug(f"Last market ask - {ask}")
    logger.debug(f"Minimum viable order - {min_notional}")
    logger.debug(f"Minimum qty per order - {min_lot_size}")
    # Check if qty input is already correct (it has to be, already ordered)
    mod_calc = shared_libs.qty_mod(purchased_qty, min_lot_size)
    if mod_calc['success'] and purchased_qty > 0:
        logger.debug("Got a good qty for the purchased executed qty")
    else:
        logger.error("Could not calc a 0 modulo of the starting qty, did you get the executed qty?????")
        return dict(success = False)

    ## Put modulo check here for qty, it should have no remainder, than we apply the modulo to the target calc below and round the remainder up
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                try:
                    num_targets = len(result.targets)
                    max_targets = int(config['targets']['max_targets_to_process'])
                    logger.debug(f"Number of Targets: {num_targets}")
                    logger.debug(f"Max Targets: {max_targets}")
                    if max_targets < num_targets:
                        logger.debug("Max target limited by config, setting max = num")
                        num_targets = max_targets
                    else:
                        logger.debug("Artificial limiting not relevant to this target, ")
                    distribution = config['targets']['distribution'][f"t{str(num_targets)}"]
                    logger.debug(f"Distribution: {distribution}")
                    distribution_qty = []
                    for i in range(num_targets):
                        qty = float(purchased_qty) * float(distribution[i])
                        logger.debug(f"Target: {i+1} - {result.targets[i]} - Distribution: {distribution[i]} - Raw Qty: {qty}")
                        clean_qty = shared_libs.qty_mod(qty, min_lot_size)
                        logger.debug(f"Target - {i+1} - Fixed Qty - {clean_qty}")
                        clean_qty['distribution'] = float(distribution[i])
                        distribution_qty.append(clean_qty)
                    logger.debug(f"Distribution of qty - {distribution_qty}")
                    check_result = 0.0
                    for q in distribution_qty:
                        check_result = check_result + q['qty']
                    logger.debug(f"Check qty result after distribution: {check_result}")
                    if float(check_result) != float(purchased_qty) and float(check_result) != 0.0:
                        logger.debug("Distribution calc variance")
                        logger.debug(f"Qty Purchased - {purchased_qty} -> Qty to sell - {check_result}")
                        variance = purchased_qty - check_result
                        logger.debug(f"Adding/Removing variance to/from first target, should be small - variance = {variance}")
                        distribution_qty[0]['qty'] = distribution_qty[0]['qty'] + variance
                        logger.debug(f"New distribution : {distribution_qty}")
                        logger.debug(f"Calculate distribution ability to sell - market min notional: {min_notional}")
                        good_to_go = True
                        for d in distribution_qty:
                            sell_ability_result = calc_target_sell_ability(d['qty'], ask, min_notional)
                            if sell_ability_result['success']:
                                logger.debug(f"can sell at current ask - {d['qty']}")
                            else:
                                logger.error(f"qty will likely result in min-notional error for the target - {d['qty']}")
                                good_to_go = False
                        if good_to_go:
                            return dict(success = True, id = idp, distribution = distribution_qty, error = "")
                        else:
                            return dict(success = False, id = idp, distribution = distribution_qty, error = "Sell ability issue")
                    else:
                        logger.debug("Distribution calc passed, no variance required")
                        logger.debug(pformat(distribution_qty))
                        logger.debug(f"Calculate distribution ability to sell - Min Notional: {min_notional}")
                        good_to_go = True
                        for d in distribution_qty:
                            sell_ability_result = calc_target_sell_ability(d['qty'], ask, min_notional)
                            if sell_ability_result['success']:
                                logger.debug(f"can sell as current ask - {d['qty']}")
                            else:
                                logger.error(f"qty will result in min-notional error - {d['qty']}")
                                good_to_go = False
                        if good_to_go:
                            logger.debug("All targets sellable")
                            time.sleep(1)
                            return dict(success = True, id = idp, distribution = distribution_qty, error = "")
                        else:
                            logger.error("Some targets not sellable")
                            time.sleep(2)
                            return dict(success = False, id = idp, distribution = distribution_qty, error = "Sell Ability Issue")
                except Exception:
                    logger.error(traceback.format_exc())
                    logger.error("Exception dealing with targeting qty checks")
                    return dict(success = False, id = idp, error = "Qty calc - exception")
            else:
                logger.trace("signal not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.trace("No signals in table")

def check_signal_funding(rawpair):
    logger.debug(f"Request signal funding - {rawpair}")
    import requests
    import json
    funding_validation = {}
    funding_validation["success"] = False
    funding_validation["error"] = ""
    funding_validation["decision"] = {}
    pair = shared_libs.split_market_pair(rawpair)
    if pair and pair["base_symbol"]:
        try:
            res = requests.get(f"{config['envoy']['host']}/binance-rest-controller/wallet")
            response = json.loads(res.text)
            logger.trace(response)
        except Exception:
            logger.error(traceback.format_exc())
            logger.error("Issue with response from binance controller")
            funding_validation["success"] = False
            funding_validation["error"] = "Issue with response from binance controller"
            return funding_validation
    else:
        logger.error("Could not determine base currency, abort!")
        funding_validation["error"] = f"Could not determine base symbol from pair info -{rawpair}"
        funding_validation["success"] = False
    if response and response["info"]["balances"]:
        logger.debug(f"received wallet data - making decision for - {pair['base_symbol'].upper()}")
        for asset in response["info"]["balances"]:
            if asset["asset"] == pair["base_symbol"].upper():
                logger.debug("Found asset")
                logger.debug(f"{config['funding']['funding_calc_model']} - {asset['free']} - {asset['asset']}")
                funding_validation["decision"] = funding_calc(config["funding"]["funding_calc_model"], float(asset["free"]), asset["asset"])
                logger.debug(funding_validation)
                if funding_validation["decision"] and funding_validation["decision"]["success"]:
                    logger.debug("We have funding")
                    funding_validation["success"] = True
                    return funding_validation
                if funding_validation["decision"] and funding_validation["decision"]["success"]:
                    logger.debug("We have insufficient funds to manage this signal")
                    funding_validation["success"] = False
                    funding_validation["error"] = "Insufficient funds"
                    return funding_validation
                else:
                    logger.debug("Issue with funding_decision routine, like exception")
                    funding_validation["success"] = False
                    funding_validation["error"] = "exception"
                    return funding_validation
    elif not response["info"]["balances"]:
        funding_validation["error"] = "Issue with wallet response, balances - " + json.dumps(response)
        funding_validation["success"] = False
    else:
        funding_validation["error"] = "Issue with wallet response - " + json.dumps(response)
        funding_validation["success"] = False
    logger.debug(pformat(funding_validation))
    return funding_validation

def fetch_signal(idp):
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.SignalModel).filter(models.SignalModel.id == int(idp))
            result = shared_libs.row2dict(session.execute(statement).scalars().first())
            if result:
                logger.trace(f"Got - {result}")
                return shared_libs.floaty_sig(result)
            else:
                logger.error(f"Signal - {idp} - not found")
                return dict(success = False, id = 0, error = f"Signal - {idp} - not found")
        except Exception:
            logger.error(f"Exception fetching signal")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def fetch_related_updates(process_id):
    from sqlalchemy import select
    session = db_session()
    if process_id:
        try:
            session.commit()
            statement = select(models.UpdateModel).filter(models.UpdateModel.signal_process_id == process_id)
            result = session.execute(statement).scalars()
            r = []
            if result:
                logger.trace(f"Got - {result}")
                i = 0
                for row in result:
                    logger.debug("Processing Row - ")
                    logger.debug(dict(row))
                    r.append(dict(row))
                logger.debug(f"Related orders count - {len(r)}")
                logger.debug("Updates - ")
                logger.debug(r)
                for u in range(len(r)):
                    r[u] = shared_libs.floaty_upd(r[u])
                logger.debug("Floated - ")
                logger.debug(r)
                ret = {}
                ret['success'] = True
                ret['updates'] = r
                return ret
            else:
                logger.error(f"Related updates - {process_id} - not found")
                return dict(success = False, id = 0, error = f"Updates - {process_id} - not found")
        except Exception:
            logger.error(f"Exception fetching updates")
            logger.error(traceback.format_exc())
            return dict(success = False, process_id = process_id, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No process id to fetch")
        return dict(success = False, process_id = process_id, error = "No ID to fetch")

def count_signals_by_tracking_number(tracking_numberp):
    from sqlalchemy import func
    session = db_session()
    if tracking_numberp:
        try:
            session.commit()
            result = session.query(func.count(models.SignalModel.tracking_number)).filter(models.SignalModel.tracking_number == tracking_numberp).scalar()
            logger.debug(result)
            if result and result > 0:
                logger.debug(f"Count of {tracking_numberp} is {result}")
                return dict(success = True, tracking_number = tracking_numberp, count = result)
            else:
                logger.error(f"Signal - {tracking_numberp} - not found")
                return dict(success = False, tracking_number = tracking_numberp, count = 0)
        except Exception:
            logger.error(f"Exception fetching count of signals")
            logger.error(traceback.format_exc())
            return dict(success = False, id = tracking_numberp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = tracking_numberp, error = "No tracking_number to fetch")

def process_order_execution_data(order_data):
    logger.debug("processing order data")
    od = json.loads(order_data)
    update_pack = {}
    if od['sell_order_success']:
        update_pack['success'] = True
        logger.debug("Order successful")
        binance_data = json.loads(od['binance_order_data'])
        update_pack['actual_qty_sold'] = float(binance_data['amount'])
        update_pack['actual_price_sold'] = float(binance_data['price'])
        update_pack['status'] = 'completed'
        update_pack['error_information'] = ''
    else:
        logger.error("order failed")
        update_pack['success'] = False
        update_pack['error_information'] = ''
        update_pack['status'] = 'failed'
        update_pack['actual_qty_sold'] = float(0.0)
        update_pack['actual_price_sold'] = float(0.0)
    logger.debug(update_pack)
    return update_pack

def store_signal(sig, is_duplicatep=False):
    session = db_session()
    try:
        stat = '00_NEW'
        signal = models.SignalModel(
            tracking_number = sig["tracking_number"],
            process_id = "",
            status = stat,
            error_information = "",
            is_duplicate = is_duplicatep,
            funding_allocated = 0.0,
            qty_purchased = 0.0,
            avg = shared_libs.percent_to_float(sig["avg"]),
            entry_high = sig["entry_high"],
            entry_low = sig["entry_low"],
            entry_actual = 0.0,
            pair = sig["pair"],
            profit = sig["profit"],
            risk = sig["risk"],
            stoploss = sig["stoploss"],
            targets = sig["targets"],
            targets_distribution = [],
            qty_remaining = 0.0
        )
        session.add(signal)
        session.commit()
        return dict(success = True, id = signal.id, error = None)
    except Exception:
        session.rollback()
        logger.error(traceback.format_exc())
        logger.error("Could not store signal")
        return dict(success = False, id = 0, error = traceback.format_exc())
    finally:
        session.close()

def new_performance_record(sig):
    session = db_session()
    try:
        perf = models.PerformanceModel(
            linked_signal_id = sig['id'],
            signal_process_id = sig['process_id'],
            tracking_number = sig['tracking_number'],
            number_of_targets = len(sig['targets']),
            market = sig['pair'],
            signal_completed = False,
            average_percent_gain = 0.0,
            status = sig['status'],
            error_information = sig['error_information'],
            funding_requested = sig['funding_allocated'],
            funding_actioned = 0.0,
            entry_price_requested = sig['entry_high'],
            entry_price_actioned = sig['entry_actual'], # Fix (fetch from binance)
            entry_qty_requested = sig['qty_purchased'],
            entry_qty_actioned = sig['qty_purchased'], # Fix (fetch from binance)
            entry_completed = 0, #fetch from vars
            target1_price_requested = 0.0,
            target1_price_actioned = 0.0,
            target1_percent_allocation = 0.0,
            target1_qty_allocated = 0.0,
            target1_qty_actioned = 0.0,
            target1_price_gain = 0.0,
            target1_completed = 0.0,
            target2_price_requested = 0.0,
            target2_price_actioned = 0.0,
            target2_percent_allocation = 0.0,
            target2_qty_allocated = 0.0,
            target2_qty_actioned = 0.0,
            target2_price_gain = 0.0,
            target2_completed = 0.0,
            target3_price_requested = 0.0,
            target3_price_actioned = 0.0,
            target3_percent_allocation = 0.0,
            target3_qty_allocated = 0.0,
            target3_qty_actioned = 0.0,
            target3_price_gain = 0.0,
            target3_completed = 0.0,
            target4_price_requested = 0.0,
            target4_price_actioned = 0.0,
            target4_percent_allocation = 0.0,
            target4_qty_allocated = 0.0,
            target4_qty_actioned = 0.0,
            target4_price_gain = 0.0,
            target4_completed = 0.0,
            settlement_price_requested = 0.0,
            settlement_price_actioned = 0.0,
            settlement_percent_allocation = 0.0,
            settlement_qty_allocated = 0.0,
            settlement_qty_actioned = 0.0,
            settlement_price_gain = 0.0,
            settlement_completed = 0.0,
        )
        session.add(perf)
        session.commit()
        return dict(success = True, id = perf.id, error = None)
    except Exception:
        session.rollback()
        logger.error(traceback.format_exc())
        logger.error("Could not store performance record")
        return dict(success = False, id = 0, error = traceback.format_exc())
    finally:
        session.close()

def populate_entry_performance(idp, signal, procvars):
    # logger.debug(f"Update signal - {tracking_number} funding information in db - {funding_validation['decision']['base_symbol_funds_allocated']}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.PerformanceModel).filter(models.PerformanceModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if signal and procvars:
                    result.funding_actioned = float(signal['funding_allocated']) #look into this, dollar -> bitcoin -> budget???
                    result.entry_price_actioned = float(procvars['entry_price']) #confirm that this is FROM THE ORDER!
                    result.entry_qty_actioned = float(procvars['qty_purchased']) #confirm that this is FROM THE ORDER!
                    result.entry_completed = True if procvars['entry_order_success'] else False
                    session.add(result)
                    session.commit()
                    return dict(success = True, id = idp, error = None)
                else:
                    logger.error("populate_entry_performance vars empty")
                    return dict(success = False, id = idp, error = f"populate_entry_performance vars empty")
            else:
                logger.error(f"Performance record - {idp} - not found")
                return dict(success = False, id = idp, error = f"performance record - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching performance record")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def populate_target_performance(idp, updates, procvars):
    # logger.debug(f"Update signal - {tracking_number} funding information in db - {funding_validation['decision']['base_symbol_funds_allocated']}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.PerformanceModel).filter(models.PerformanceModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if updates and procvars:
                    for update in updates:
                        if update['update_type'] == "FirstTargetReached":
                            upt = "FirstTargetReached_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            logger.debug("od")
                            logger.debug(pformat(od))
                            logger.debug("binance")
                            logger.debug(pformat(od['binance_order_data']))
                            logger.debug(bd)
                            result.target1_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.target1_price_requested = float(update['target_price'])
                            result.target1_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.target1_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.target1_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.target1_qty_actioned = float(bd['filled']) # what came back from binance
                            result.target1_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "SecondTargetReached":
                            upt = "SecondTargetReached_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.target2_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.target2_price_requested = float(update['target_price'])
                            result.target2_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.target2_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.target2_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.target2_qty_actioned = float(bd['filled']) # what came back from binance
                            result.target2_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "ThirdTargetReached":
                            upt = "ThirdTargetReached_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.target3_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.target3_price_requested = float(update['target_price'])
                            result.target3_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.target3_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.target3_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.target3_qty_actioned = float(bd['filled']) # what came back from binance
                            result.target3_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "FourthTargetReached":
                            upt = "FourthTargetReached_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.target4_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.target4_price_requested = float(update['target_price'])
                            result.target4_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.target4_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.target4_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.target4_qty_actioned = float(bd['filled']) # what came back from binance
                            result.target4_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "AllTargetsReachedMessage":
                            upt = "AllTargetsReachedMessage_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.target4_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.target4_price_requested = float(update['target_price'])
                            result.target4_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.target4_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.target4_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.target4_qty_actioned = float(bd['filled']) # what came back from binance
                            result.target4_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "StoplossReachedMessage":
                            upt = "StoplossReachedMessage_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.settlement_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.settlement_price_requested = float(update['target_price'])
                            result.settlement_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.settlement_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.settlement_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.settlement_qty_actioned = float(bd['filled']) # what came back from binance
                            result.settlement_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "LimitedFailureMessage":
                            upt = "LimitedFailureMessage_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.settlement_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.settlement_price_requested = float(update['target_price'])
                            result.settlement_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.settlement_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.settlement_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.settlement_qty_actioned = float(bd['filled']) # what came back from binance
                            result.settlement_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                        if update['update_type'] == "SignalExpiryMessage":
                            upt = "SignalExpiryMessage_order_info"
                            logger.debug(pformat(json.loads(procvars[upt])))
                            od = json.loads(procvars[upt])
                            bd = json.loads(od['binance_order_data'])
                            result.settlement_completed = True if od['sell_order_success'] else False # fetch from order process
                            result.settlement_price_requested = float(update['target_price'])
                            result.settlement_price_actioned = float(bd['price']) # What came back from binance (market order)
                            result.settlement_percent_allocation = float(od['qty_sold']) / float(od['qty_purchased'])  # what was the split from funding
                            result.settlement_qty_allocated = float(od['qty_sold']) # what was sent to sell/order
                            result.settlement_qty_actioned = float(bd['filled']) # what came back from binance
                            result.settlement_price_gain = (float(bd['price']) - float(procvars['entry_price'])) / float(procvars['entry_price']) # small calc
                            session.add(result)
                            session.commit()
                    return dict(success = True, id = idp, error = None)
                else:
                    logger.error("populate_entry_performance vars empty")
                    session.rollback()
                    return dict(success = False, id = idp, error = f"populate_entry_performance vars empty")
            else:
                logger.error(f"Performance record - {idp} - not found")
                session.rollback()
                return dict(success = False, id = idp, error = f"performance record - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching performance record")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def db_keep_alive():
    logger.trace("DB keep alive")
    session = db_session()
    try:
        result = session.execute('SELECT 1')
        for r in result:
            logger.trace(f"{r}")
    except Exception:
        logger.error(f"Exception with keep alive")
        session.rollback()
        logger.error(traceback.format_exc())
    finally:
        session.close()