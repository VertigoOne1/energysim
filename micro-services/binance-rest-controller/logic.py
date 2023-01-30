#!/bin/python3

from curses import savetty
import sys
from typing import final
sys.path.append(r'./modules')

import json, requests, socket, time, re, traceback
from envyaml import EnvYAML
import os, fnmatch
from pprint import pformat
from random import randint
import modules.defconfig as defconfig, modules.eventbus as eventbus, apicontroller
import binance, binanceMock
import metrics, models
import modules.shared_libs as shared_libs, modules.events as events
from modules.logger import setup_custom_logger
from modules.database import db_session

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

def consume(topic, group):
    from kafka import KafkaConsumer
    from marshmallow import ValidationError
    consumer = KafkaConsumer(bootstrap_servers=BROKER_URL,group_id=group,
                            auto_offset_reset=config["kafka"]["auto_offset_reset"], enable_auto_commit=True,
                            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
    consumer.subscribe(topic)
    for message in consumer:
        data = message.value
        metrics.p_events_consumed.inc()
        logger.trace(pformat(data))
        event_schema = events.EventSchema()
        event = {}
        req = {}
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
                if event["etype"] == events.EventTypes.BINANCE_TRADE_DATA_REQUEST.value:
                    req_schema = events.BinanceTradeDataRequestEventSchema()
                    try:
                        req = req_schema.loads(json.dumps(event["payload"]))
                        logger.trace(pformat(req))
                        if process_market_data_request_event(req):
                            logger.info("Market data request processed")
                    except ValidationError as err:
                        logger.error(err.messages)
                        logger.error(err.valid_data)
                        logger.error("Malformed payload skipped")
                        metrics.p_payload_validation_errors.inc()
                elif event["etype"] == events.EventTypes.BINANCE_TRADE_DATA_REQUEST.value:
                    logger.trace("Ignoring trade data request event etype")
                elif event["etype"] == events.EventTypes.BINANCE_TRADE_DATA.value:
                    logger.trace("Ignoring trade data event etype")
                else:
                    logger.warn("Event etype not handled by this service")
            except KeyError as err:
                logger.error(pformat(err))

def process_market_data_request_event(req):
    if config["binance"]["mock"]:
        logger.trace("Mocked event fire")
        ticker = binanceMock.fetch_ticker(req["pair"])
        logger.trace(ticker)
        return True
    else:
        return False

def fetch_order(idp):
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.OrderModel).filter(models.OrderModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.debug(f"Got Order - {result}")
                return result
            else:
                logger.error(f"order - {idp} - not found")
                return dict(success = False, id = 0, error = f"Order - {idp} - not found")
        except Exception:
            logger.error(f"Exception fetching order")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_order_status(idp, tracking_number, order_type, status, error_information, order_data, order_id):
    logger.debug(f"Update order - {idp} - {tracking_number} - {status}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.OrderModel).filter(models.OrderModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if status:
                    result.status = status
                if error_information:
                    result.error_information = error_information
                if order_data:
                    result.order_data = json.dumps(order_data)
                if order_id:
                    result.order_id = order_id
                if order_type:
                    result.order_type = order_type
                if tracking_number:
                    result.tracking_number = tracking_number
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Order - {idp} - {tracking_number} - not found")
                return dict(success = False, id = idp, error = f"Order - {idp} - {tracking_number} - not found")
        except Exception:
            logger.error(f"Exception fetching order")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        session.close()
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_order_executed_price_qty(idp, executed_price=None, executed_qty=None):
    logger.debug(f"Update order - {idp} - {executed_price}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.OrderModel).filter(models.OrderModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if executed_price is not None:
                    result.executed_price = executed_price
                if executed_qty is not None:
                    result.executed_qty = executed_qty
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Order - {idp} - not found")
                return dict(success = False, id = idp, error = f"Order - {idp}- not found")
        except Exception:
            logger.error(f"Exception fetching order")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

# If the order is bigger than the market minimums
# if the order is bigger than the wallet balance, then we need to calculate a new qty/cost that fits in that balance
# but we don't know how much do we want to sell because the order is bigger for which target
# Since were already trying to sell more than we have, we can sell all

# the qty free is more than the minimum, the cost is more than the minimum, but less than the wallet
# the options are, sell the minimum, or sell everything. were already trying to sell more than everything so i
# think we default to sell everything. The sale is either a stoploss, which has to sell everything
# or a target, trying to sell more than everything, thus sell everything anyway.

# If what we want to sell is less than viable, then make it the smallest it can be that is viable

def create_spot_market_sell_order(order_table_id, tracking_number, market, qty, price, order_type):
    viability = check_fix_sell_order_versus_wallet(tracking_number, market, qty, price)
    logger.debug("Viability - ")
    logger.debug(f"{viability}")
    if viability["status"] == "passed":
        logger.info(f"Viable order possible creating order - {tracking_number}")
        result = binance.create_market_sell_order(tracking_number, market, viability['qty'], price)
        result["original_qty"] = qty
        result["viable_qty"] = viability['qty']
        result["viability_info"] = viability
        logger.debug(pformat(result))
        if result["status"] == "passed":
            logger.info(f"Binance market order created, commiting info to table - {tracking_number}")
            update_order_status(order_table_id, tracking_number, order_type, result["status"], result["error_information"], result["order_data"], result["order_id"])
            update_order_executed_price_qty(order_table_id, result['order_data']["price"], result['order_data']["amount"])
            result['success'] = True
            return result
        else:
            logger.warn(f"Order creation failed - {tracking_number}")
            update_order_status(order_table_id, tracking_number, order_type, result["status"], result["error_information"], result["order_data"], result["tracking_number"])
            result['success'] = False
            return result
    else:
        logger.debug("Viable order not possible")
        viability["error_information"] = "The order failed viability checks"
        update_order_status(order_table_id, tracking_number, order_type, viability["status"], viability["error_information"], "", "")
        viability['success'] = False
        return viability

def create_spot_market_buy_order(order_table_id, tracking_number, market, qty, price, order_type):
    try:
        result = binance.create_market_buy_order(tracking_number, market, qty, price)
        update_order_status(order_table_id, tracking_number, order_type, result["status"], result["error_information"], result["order_data"], result["order_id"])
        update_order_executed_price_qty(order_table_id, result['order_data']["price"], result['order_data']["amount"])
        if result["status"] == "passed":
            result['success'] = True
            logger.info("Binance market order created")
            return result
        else:
            update_order_status(order_table_id, tracking_number, order_type, result["status"], result["error_information"], result["order_data"], result["order_id"])
            logger.error("Binance market order created")
            result['success'] = False
            return result
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Could not store order")
        return dict(success = False, id = 0, error = traceback.format_exc())

def check_fix_sell_order_versus_wallet(tracking_number, market, qty, price):
    mock = config["binance"]["mock"]
    result = {}
    result['status'] = "init"
    result['qty'] = qty
    result['price'] = price
    result['market'] = shared_libs.split_market_pair(market)
    result["tracking_number"] = tracking_number
    result['success'] = False
    wallet = binance.fetch_wallet_information()
    matched_asset = False
    # result["wallet"] = wallet # It is very big object, and unnecessary
    logger.debug(f"Checking wallet for market - {market} - trade - {result['market']['trade_symbol']}")
    for bal in wallet["info"]["balances"]:
        asset = bal['asset']
        logger.trace(f"asset - {asset}")
        free = shared_libs.str_to_float(bal["free"])
        locked = shared_libs.str_to_float(bal["locked"])
        total = shared_libs.str_to_float(bal["free"]) +  shared_libs.str_to_float(bal["locked"])
        if asset == result['market']["trade_symbol"]:
            logger.debug(f"Market matched to a wallet asset - {market} - {asset} - {result['market']['trade_symbol']}")
            matched_asset = True
            if free > 0.0 and not mock:
                logger.debug("Greater than 0 balance, continue checks")
                try:
                    viability = check_order_viability(market, qty, price)
                    logger.debug(f"Minimum qty - {viability['minimum_qty']}")
                    logger.debug(f"Minimum cost - {viability['minimum_cost']}")
                    logger.debug(f"Current order cost - {viability['order_cost']}")
                    logger.debug(f"Minumum order cost - {viability['minimum_cost']}")
                except Exception as e:
                    logger.error("Issue with viability check")
                    logger.error(e, exc_info=True)
                    viability["status"] == "exception"
                    result["qty"] = free
                    result["status"] = "failed"
                    logger.debug(pformat(result))
                    logger.debug(pformat(viability))
                    return result
                if viability["status"] == "passed":
                    logger.debug("Order passed minimum market viability")
                    logger.debug("Checking balance viability")
                    if qty > free:
                        logger.error(f"Trying to sell more than we have, calculate sell all scenario viability")
                        if (free * price) >= viability['minimum_cost']:
                            logger.debug("Selling everything will pass viability")
                            result["qty"] = free
                            result["status"] = "passed"
                            logger.debug(pformat(result))
                            return result
                        else:
                            logger.error("Selling everything fails market viability too, whoops")
                            result["status"] = "failed"
                            return result
                    elif qty <= free:
                        logger.debug(f"Wallet balance can do the order as is, proceed")
                        result["status"] = "passed"
                        logger.debug(pformat(result))
                        return result
                    else:
                        logger.debug("How did we get here")
                        result["status"] = "failed"
                        return result
                elif viability["status"] == "failed":
                    logger.debug("Order is too small for the market, can we use the smallest order with our wallet balance?")
                    if free < viability['minimum_qty']:
                        logger.error("We cannot create the smallest order with the current balance")
                        result["status"] = "failed"
                        logger.debug(result)
                        return result
                    else:
                        logger.debug("The balance available can create the smallest order, lets set it")
                        if (viability['minimum_qty'] * price) >= viability['minimum_cost']:
                            logger.debug("Selling the minimum allowed qty is fine cost wise at current price")
                            result["status"] = "passed"
                            result["qty"] = viability['minimum_qty']
                            logger.debug(pformat(result))
                            return result
                        else:
                            logger.debug("At the current price with minimum qty, it is not at market minimum cost")
                            logger.debug("Calculate minimum qty to reach minimum cost")
                            new_qty = viability['minimum_cost'] / price
                            logger.warn(f"Need to sell at least - {new_qty} to be able to create an order")
                            if new_qty > free:
                                logger.error("Cannot create an order with minimum cost with current balance")
                                logger.error(f"Minimum Qty - {new_qty} - Balance Free - {free}")
                                result["status"] = "failed"
                                return result
                            else:
                                logger.debug("Order can be done at mininimum qty required")
                                result["qty"] = new_qty
                                return result
                else:
                    logger.error("Unmatched condition!")
                    result["status"] = "failed"
                    return result
            elif mock:
                logger.warn("Mock active - We assume there is a balance!")
                result["status"] = "passed"
                result["qty"] = qty
                logger.debug(pformat(result))
                return result
            else:
                logger.debug(f"No balance for asset - {asset} - cannot sell what you don't have")
                result["status"] = "failed"
                result["qty"] = qty
                return result
    if not matched_asset:
        logger.error(f"Asset not found on wallet list")
        result["status"] = "failed"
        result["qty"] = qty
        return result
    else:
        logger.error('How are you here')
        result["status"] = "failed"
        result["qty"] = qty
        return result

def validate_spot_market_buy_order(order_id, pair, table_order_id):
    result = {}
    logger.info("IMPLEMENT VALIDATION THAT ORDER COMPLETED HERE")
    result["status"] = "not implemented"
    result["order_data"] = binance.fetch_binance_order(order_id, pair, table_order_id)
    logger.debug(f"{result}")
    if result['order_data']:
        result['success'] = True
    else:
        result["success"] = False

    ## Some ifs required to set status to completed, FILLED 100%.. etc etc

    return result

def validate_spot_market_sell_order(order_id, pair, table_order_id):
    result = {}
    logger.info("IMPLEMENT VALIDATION THAT ORDER COMPLETED HERE")
    result["status"] = "not implemented"
    result["order_data"] = binance.fetch_binance_order(order_id, pair, table_order_id)
    logger.debug(f"{result}")
    if result['order_data']:
        result['success'] = True
    else:
        result["success"] = False
    ## Some ifs required to set status to completed, FILLED 100%.. etc etc
    return result

def check_binance_order_status(tracking_number):
    logger.debug("MARNUS - use the tracking number to fetch the order id, and ask binance for status")
    logger.debug("This is to verify that the order was definitely done")
    return True

def check_order_viability(pair, qty, price):
    result = {}
    result["qty"] = qty
    result["price"] = price
    market = binance.fetch_pair_market(pair)
    if market:
        logger.debug(f"Minimum Qty - {market['limits']['amount']['min']}- trade_symbol_qty - {qty}")
        result["minimum_qty"] = float(market['limits']['amount']['min'])
        result["minimum_cost"] = float(market['limits']['cost']['min'])
        result["order_cost"] = qty * price
        result["minimum_cost"] = result["minimum_cost"] * result["minimum_qty"]
        logger.debug(f"Minimum Order Cost - {market['limits']['cost']['min']} - order_cost - {result['order_cost']}")
        if result["order_cost"] < market['limits']['cost']['min']:
            logger.debug("Order cost less than the minimum order size limit")
            result["status"] = "failed"
            result["error"] = "Order cost less than the minimum order size limit"
            logger.debug(pformat(result))
        elif result["qty"] < market['limits']['amount']['min']:
            logger.debug("Insufficient qty allocated to create a trade for this symbol")
            result["status"] = "failed"
            result["error"] = "Insufficient qty allocated to create a trade for this symbol"
            logger.debug(pformat(result))
        else:
            result["status"] = "passed"
        logger.trace(pformat(result))
        return result
    else:
        result["status"] = "failed"
        result["error"] = "could not retrieve market for this pair"
        logger.trace(pformat(result))
        return result

def check_target_vs_market(pair, target_price):
    result = {}
    result["status"] = "init"
    current_ticker = binance.fetch_ticker(pair)
    logger.trace(current_ticker)
    # Are the targets more than 3 times bigger or smaller than the current bid?
    try:
        target_variance = target_price / float(current_ticker['bid'])
    except:
        logger.error("Could not calculate target variance")
        logger.error(f"{pair} - {target_price} - Current bid - {current_ticker['bid']}")
        result["status"] = "failed"
    if target_variance < 0.96:
        logger.error(f"Target is more than 4% lower than current market bid - {target_variance}")
        result["status"] = "under"
        result["error"] = "Bid variance lower than 4%"
        result["target_price_bid_variance"] = target_variance
        return result
    elif target_variance > 1.04:
        logger.error(f"Target is more than 4% higher than current market bid - {target_variance}")
        result["error"] = "Bid variance higher than 4%"
        result["target_price_bid_variance"] = target_variance
        result["status"] = "over"
        return result
    else:
        logger.info("Target Price variance - " + str(target_variance))
        result["error"] = ""
        result["target_price_bid_variance"] = target_variance
        result["status"] = "passed"
        return result

def trade_data_response_event(pair, data):
    logger.trace("Emitting trade data - " + pair + " - data - " + data)
    do_emit = True
    if do_emit:
        event_payload = events.BinanceTradeDataEvent(pair, data)
        logger.trace("Constructed Event Payload - ")
        logger.trace(pformat(event_payload))
        payload_schema = events.BinanceTradeDataEventSchema()
        payload = payload_schema.dump(event_payload)
        logger.trace(pformat(payload))
        event_base = events.Event(events.EventTypes.BINANCE_TRADE_DATA.value, payload)
        base_schema = events.EventSchema()
        logger.trace("Constructed Event Package - ")
        logger.trace(pformat(event_base))
        logger.trace(pformat(base_schema))
        eventbus.emit(TOPIC_PREFIX+config['kafka']["binance_trade_data_topic"], base_schema.dumps(event_base))
        metrics.p_events_emitted.inc()
        return True
    else:
        logger.error("Event emission disabled in code")
        return False

def store_new_market_order(tracking_number, pair, order_type, qty, price, origin_process_id):
    session = db_session()
    try:
        market_order = models.OrderModel(
            tracking_number = tracking_number,
            market = pair,
            order_type = order_type,
            qty = qty,
            executed_qty = 0.0,
            price = price,
            executed_price = 0.0,
            status = "NEW",
            error_information = "",
            message = "",
            order_id = "",
            order_data = json.dumps({}),
            origin_process_id = origin_process_id
            )
        session.add(market_order)
        session.commit()
        return dict(success = True, id = market_order.id, error = None)
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Could not store order")
        return dict(success = False, id = 0, error = traceback.format_exc())
    finally:
        session.close()

def store_wallet_information(balances):
    for bal in balances["info"]["balances"]:
        balance = models.WalletModel(
            asset = bal["asset"],
            free = shared_libs.str_to_float(bal["free"]),
            locked = shared_libs.str_to_float(bal["locked"]),
            total = shared_libs.str_to_float(bal["free"]) +  shared_libs.str_to_float(bal["locked"])
        )
        session = db_session()
        try:
            session.add(balance)
            session.commit()
        except Exception as e:
            logger.error("Issue inserting wallet info into DB")
            logger.error(e, exc_info=True)
        finally:
            session.close()
    return (True)

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