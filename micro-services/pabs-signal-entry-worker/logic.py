#!/bin/python3

import sys, traceback
from typing import final
sys.path.append(r'./modules')

import requests, socket, time, re, json
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

freeze_trade_data_processing = False

def consume2(topic, group):
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
        try:
            event = event_schema.loads(data)
        except ValidationError as err:
            logger.warn(err.messages)
            logger.warn(err.valid_data)
            logger.warn("Malformed event skipped")
            metrics.p_event_validation_errors.inc()
            event = {}
        if event:
            logger.trace(pformat(event))
            metrics.p_events_valid.inc()
            try:
                if event["etype"] == events.EventTypes.BINANCE_TRADE_DATA.value:
                    logger.trace("Processing trade data event etype")
                    trade_data_schema = events.BinanceTradeDataEventSchema()
                    try:
                        logger.debug("Event Received - ")
                        logger.debug(pformat(event))
                        trade_data = trade_data_schema.loads(json.dumps(event["payload"]))
                        active_markets = fetch_active_markets_by_pair(trade_data["trade_data"]["symbol"])
                        logger.trace(active_markets)
                        if len(active_markets['active_markets']) > 0:
                            for market in active_markets['active_markets']:
                                logger.debug(f"{market}")
                                logger.debug(f"Process trade data for - {market.tracking_number} - {market.process_id}")
                                if market.feed_validated:
                                    logger.debug("Market feed validated")
                                    process_status = bpm.fetch_activities_by_process_id(market.process_id)
                                    logger.trace(f"{process_status}")
                                    if process_status['success']:
                                        active_task = bpm.resolve_current_process_task(process_status)
                                        logger.debug(f"{active_task}")
                                        if active_task["success"]:
                                            logger.debug("Active task retrieved, checking process state")
                                            if active_task["activity_id"] == "MarketDataReceived" or active_task["activity_id"] == "EntryMonitoringGateway":
                                                logger.debug("Trade data is expected")
                                                process_result = process_new_trade_data_event(market, trade_data)
                                                if process_result['success']:
                                                    logger.trace(f"trade data processed for {market.tracking_number}")
                                                else:
                                                    logger.warn("trade data processing failure")
                                                    logger.warn(f"{process_result}")
                                                    time.sleep(5)
                                            else:
                                                logger.error("data is not expected, but ok")
                                                # update_entry_status(market.id, market.tracking_number, "active", "", "")
                                                # request_stop_trade_data(market.tracking_number, market.pair, "trade")
                                        else:
                                            logger.error("data is not expected, but ok")
                                            # update_entry_status(market.id, market.tracking_number, "active", "", "")
                                            # request_stop_trade_data(market.tracking_number, market.pair, "trade")
                                    else:
                                        logger.debug("Process not found, turning it off")
                                        result = request_stop_trade_data(market.tracking_number, market.pair, "trade")
                                        if result['success']:
                                            update_entry_status(market.id, "in-active", "process_not_found","process_not_found", "off")
                                        else:
                                            logger.error("Issue stopping market feed")

                                else:
                                    logger.info("Validating Market Feed")
                                    bpm_result = bpm.bpm_send_message(market.process_id, market.tracking_number, "MarketDataReceived", {})
                                    logger.debug(f"{bpm_result}")
                                    if bpm_result["success"]:
                                        logger.trace("Successfully emitted bpm message")
                                        update_entry_feed_valid(market.id, True)
                                    elif "MismatchingMessageCorrelationException" in bpm_result["response"]["message"]:
                                        logger.warn("Process likely already moved on, this is, ok, db may just be a little behind")
                                        update_entry_feed_valid(market.id, True)
                                    else:
                                        logger.error("Bad response from Camunda, not validating feed")
                                        time.sleep(5)
                        else:
                            logger.debug("No active markets, skipping event")
                    except Exception:
                        logger.error(traceback.format_exc())
                        logger.error("Issue processing trade data")
                        metrics.p_payload_validation_errors.inc()
                else:
                    logger.trace("Event etype not handled by this service")
            except Exception:
                logger.error(traceback.format_exc())
                logger.error("Issue processing event")

def check_entry_zone(trade_data, active_market):
    entry_status = {}
    entry_status["entry_status"] = "invalid"
    entry_status["entry_price"] = 0.0
    entry_status["process_id"] = ""
    entry = fetch_entry_record(active_market.id)["result"]
    logger.debug(f"{entry.entry_high}")
    # Mocks first
    if config['general']['mock']:
        logger.warn("Mock engaged!")
        logger.warn("Mock engaged!")
        logger.warn("Mock engaged!")
        if config['general']['mock_state'] == 'spot-buy-market':
            logger.info(f"Signal is in the mocked zone - buy it - Entry - {entry.entry_low} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-buy-market"
            entry_status["entry_price"] = entry.entry_high
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "in_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif config['general']['mock_state'] == 'spot-below':
            logger.debug(f"Signal is below the mocked zone - wait - Stoploss - {entry.stoploss} - Entry - {entry.entry_low} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-below"
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "below_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif config['general']['mock_state'] == 'spot-above':
            logger.debug(f"Signal is above the mocked zone - wait - Entry - {entry.entry_high} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-above"
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "above_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif config['general']['mock_state'] == 'spot-stoploss':
            logger.info(f"Signal is at/below mocked stoploss - abandon - Stoploss - {entry.stoploss} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-stoploss"
            entry_status["entry_price"] = entry.stoploss
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "stoploss", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        logger.warn("Mock engaged!")
        logger.warn("Mock engaged!")
        logger.warn("Mock engaged!")
        logger.debug(entry_status)
        return entry_status
    # logger.debug(f"{entry}")
    elif not config['general']['mock']:
        if float(trade_data["price"]) <= entry.entry_high and float(trade_data["price"]) >= entry.entry_low:
            logger.info(f"Signal is in the zone - buy it - Entry - {entry.entry_low} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-buy-market"
            entry_status["entry_price"] = float(trade_data["price"])
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "in_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif float(trade_data["price"]) < entry.entry_low:
            logger.debug(f"Signal is below the zone - wait - Stoploss - {entry.stoploss} - Entry - {entry.entry_low} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-below"
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "below_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif float(trade_data["price"]) > entry.entry_high:
            logger.debug(f"Signal is above the zone - wait - Entry - {entry.entry_high} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-above"
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "above_zone", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        elif float(trade_data["price"]) <= entry.stoploss:
            logger.info(f"Signal is at/below stoploss - abandon - Stoploss - {entry.stoploss} - Current - {trade_data['price']}")
            entry_status["entry_status"] = "spot-stoploss"
            entry_status["entry_price"] = float(trade_data["price"])
            entry_status["process_id"] = str(entry.process_id)
            update_entry_status(entry.id, "active", "stoploss", "", "")
            update_entry_price(entry.id, float(trade_data["price"]))
        logger.debug(entry_status)
        return entry_status
    else:
        logger.error("Mock config invalid/missing")
        sys.exit(1)

def process_new_trade_data_event(active_market, trade_data):
    logger.trace(pformat(trade_data))
    logger.trace(pformat(active_market))
    entry_status = {}
    try:
        if active_market:
            logger.trace(pformat(active_market))
            market_pair = shared_libs.split_market_pair(active_market.pair)
            logger.trace(f"{market_pair}")
            if market_pair["condensed_upper_pair"] == trade_data["trade_data"]["symbol"]:
                logger.debug(f"Matched pair and symbol to entry needing data - {active_market.id}")
                entry_status = check_entry_zone(trade_data["trade_data"], active_market)
                logger.debug(pformat(entry_status))
                if entry_status["entry_status"] == "spot-buy-market":
                    update_entry_status(active_market.id, "ENTRY_ZONE_MATCHED", f"{entry_status}", "", "")
                    logger.debug("Send BPM message to buy")
                    try:
                        message_send_result = bpm.bpm_send_message(entry_status["process_id"], active_market.tracking_number, "EntryPointReached", entry_status)
                        if message_send_result["success"]:
                            logger.debug("Notification success")
                            update_entry_actual(active_market.id, float(trade_data["trade_data"]["price"]))
                            return dict(success = True, entry_status = entry_status, error = None, message_send_result = message_send_result)
                        else:
                            logger.error("Issue sending notification")
                            return dict(success = False, entry_status = entry_status, error = message_send_result['response'])
                    except Exception:
                        logger.debug("Issue sending BPM message")
                        logger.debug("IF things move too fast, it is possible that the message is sent before camunda is ready")
                        logger.debug("The expectation is that were not matching an entry point within 15 seconds, so this should not happen, but it might")
                        logger.error(traceback.format_exc())
                        return dict(success = False, entry_status = entry_status, error = traceback.format_exc())
                elif entry_status["entry_status"] == "spot-stoploss":
                    logger.info("SEND MESSAGE TO SELL, this should not happen, as we have not bought anything yet!")
                    update_entry_status(active_market.id, "STOPLOSS_MATCHED", f"{entry_status}", "", "")
                else:
                    logger.debug(f"entry is - {entry_status['entry_status']}")
                    update_entry_status(active_market.id, "", f"{entry_status}", "", "")
            else:
                logger.trace("No entry needs this data")
        else:
            logger.trace("Ignoring trade data, we don't have entries, probably old kafka events")
        time.sleep(1)
        return dict(success = True, entry_status = entry_status, error = None)
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Could not process trade event data")
        return dict(success = False, entry_status = entry_status, error = traceback.format_exc())

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
        logger.error("Issue with response from binance rest controller")
        return {}

def request_start_trade_data(tracking_number, pair, type):
    import requests
    import json
    logger.debug(f"Requesting feed for - {tracking_number} - {pair} - {type}")
    try:
        url = f"{config['envoy']['host']}/binance-ws-controller/ws_stream?market={pair}&tracking_number={tracking_number}&type={type}"
        res = requests.get(url)
        logger.debug(f"Response - {res}")
        response = json.loads(res.text)
        logger.debug(response)
        if response['success']:
            return response
        else:
            return dict(success = False, tracking_number = tracking_number, error = "WS response failure")
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue communicating with binance websocket controller")
        return dict(success = False, tracking_number = tracking_number, error = traceback.format_exc())

def request_stop_trade_data(tracking_number, pair, type):
    import requests
    import json
    try:
        url = f"{config['envoy']['host']}/binance-ws-controller/ws_stream?market={pair}&tracking_number={tracking_number}&type={type}"
        res = requests.delete(url)
        response = json.loads(res.text)
        logger.debug(response)
        if response['success']:
            return response
        else:
            return dict(success = False, tracking_number = tracking_number, error = "WS response failure")
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue communicating with binance websocket controller")
        return dict(success = False, tracking_number = tracking_number, error = traceback.format_exc())

def new_entry_record(entryp, proc_id):
    session = db_session()
    try:
        stat = '00_NEW'
        entry = models.EntryModel(
            tracking_number = entryp["tracking_number"],
            pair = entryp["pair"],
            process_id = proc_id,
            entry_high = entryp["entry_high"],
            entry_low = entryp["entry_low"],
            entry_actual = 0.0,
            status = stat,
            error_information = "",
            last_price = 0.0,
            entry_status = "NEW",
            ws_status = "",
            stoploss = entryp["stoploss"],
            feed_validated = False
        )
        session.add(entry)
        session.commit()
        return dict(success = True, id = entry.id, error = None)
    except Exception:
        session.rollback()
        logger.error(traceback.format_exc())
        logger.error("Could not store signal")
        return dict(success = False, id = 0, error = traceback.format_exc())
    finally:
        session.close()

def update_entry_status(idp, status, entry_status, error_information, ws_status):
    logger.debug(f"UpdateDB - entry - {idp} - {status} - {entry_status} - {error_information} - {ws_status}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if status:
                    result.status = status
                if entry_status:
                    result.entry_status = entry_status
                if entry_status:
                    result.ws_status = ws_status
                if error_information:
                    result.error_information = error_information
                if ws_status:
                    result.ws_status = ws_status
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Entry - {idp} - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_entry_feed_valid(idp, feed_valid):
    logger.debug(f"UpdateDB - entry - {idp} - {feed_valid}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if feed_valid:
                    result.feed_validated = feed_valid
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Entry - {idp} - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_entry_price(idp, last_price):
    logger.trace("Update entry pricing record in db")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if last_price:
                    result.last_price = last_price
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Entry - {idp}  - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_entry_actual(idp, actual_price):
    logger.trace("Update entry pricing record in db")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if actual_price:
                    result.entry_actual = actual_price
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Entry - {idp}  - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def update_entry_process_id(idp, process_id):
    logger.trace("Update entry process_id in db")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if process_id:
                    result.process_id = process_id
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Entry - {idp}  - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No ID to fetch")

def fetch_active_markets():
    logger.trace("Fetch active markets")
    from sqlalchemy import select
    session = db_session()
    try:
        statement = select(models.EntryModel.c.id, models.EntryModel.c.pair).filter(models.EntryModel.entry_status == "active")
        result = session.execute(statement).scalars().all()
        if result:
            logger.info("WHAT DOES THE ACTIVE MARKETS OBJECT LOOK LIKE")
            logger.debug(f"{result}")
            result["success"] = True
            return result
        else:
            logger.warn(f"No active markets")
            return dict(success = True, active_markets = result)
    except Exception:
        session.rollback()
        logger.error(f"Exception fetching active markets")
        logger.error(traceback.format_exc())
        return dict(success = False, error = traceback.format_exc())
    finally:
        session.close()

def fetch_active_markets_by_pair(pairp):
    logger.trace(f"Fetch active markets by pair - {pairp}")
    pairmatch = shared_libs.split_market_pair(pairp)
    logger.debug(f"{pairmatch}")
    from sqlalchemy import select
    session = db_session()
    try:
        session.commit()
        statement = select(models.EntryModel).filter(models.EntryModel.pair == pairmatch["split_upper_pair"], models.EntryModel.status == 'active')
        result = session.execute(statement).scalars().all()
        if result:
            logger.debug("Found active markets for that pair")
            return dict(success = True, active_markets = result)
        else:
            logger.warn(f"No markets using that pair")
            return dict(success = True, active_markets = {})
    except Exception:
        session.rollback()
        logger.error(f"Exception fetching active markets")
        logger.error(traceback.format_exc())
        return dict(success = False, active_markets = {}, error = traceback.format_exc())
    finally:
        session.close()

def fetch_entry_record(idp):
    logger.trace("Fetch entry record")
    from sqlalchemy import select, desc
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.EntryModel).filter(models.EntryModel.id == int(idp)).order_by(desc(models.EntryModel.id))
            result = session.execute(statement).scalars().first()
            if result:
                return dict(success = True, result = result, error = None)
            else:
                logger.error(f"Entry - {idp}  - not found")
                return dict(success = False, id = idp, error = f"Entry - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Entry")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        session.close()
        logger.error("No ID to fetch")
        return dict(success = False, id = idp, error = "No entry ID to fetch")

def signal_update_event(tracking_number, update_type, status, message, entry_price):
    logger.trace(f"Sending signal update event - {tracking_number} - status - {status}  message - {message} - price - {entry_price}")
    do_emit = True
    if do_emit:
        event_payload = events.PabsSignalUpdateEvent(tracking_number, update_type, status, message, entry_price)
        logger.trace("Constructed Event Payload - ")
        logger.trace(pformat(event_payload))
        payload_schema = events.PabsSignalUpdateEventSchema()
        payload = payload_schema.dump(event_payload)
        logger.trace(pformat(payload))
        event_base = events.Event(events.EventTypes.PABS_SIGNAL_UPDATE.value, payload)
        base_schema = events.EventSchema()
        logger.trace("Constructed Event Package - ")
        logger.trace(pformat(event_base))
        logger.trace(pformat(base_schema))
        eventbus.emit(TOPIC_PREFIX+config['kafka']["signals_topic"], base_schema.dumps(event_base))
        metrics.p_events_emitted.inc()
        return True
    else:
        logger.error("Problems detected, see debug")
        return False
        # Build failed event log here

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