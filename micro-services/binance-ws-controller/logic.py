#!/bin/python3

import traceback
import sys
sys.path.append(r'./modules')

import json, requests, socket, time, re
from envyaml import EnvYAML
import os, fnmatch
from pprint import pformat
from random import randint
from uuid import UUID
import modules.defconfig as defconfig, modules.eventbus as eventbus, apicontroller
import binanceint
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

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)

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
                            logger.debug("Trade data request processed")
                    except ValidationError as err:
                        logger.error(err.messages)
                        logger.error(err.valid_data)
                        logger.error("Malformed payload skipped")
                        metrics.p_payload_validation_errors.inc()
                elif event["etype"] == events.EventTypes.BINANCE_TRADE_DATA.value:
                    logger.trace("Ignoring trade data event etype")
                else:
                    logger.warn("Event etype not handled by this service")
            except KeyError as err:
                logger.error(pformat(err))

def start_ws_stream(pair, tracking_number, type):
    logger.debug(f"Setup WS Ticker - {pair}")
    if pair and len(pair) > 0:
        response = binanceint.start_ws_stream(pair, tracking_number, type)
        logger.trace(pformat(response))
        metrics.p_feeds_requested.inc()
        if response["status"] == "started":
            logger.debug(f"Feed started - {response['pair']}")
            response["status"] = "active"
            response["success"] = True
        elif response["status"] == "existing":
            logger.debug(f"Feed Existing - {response['pair']}")
            response["status"] == "active"
            response["success"] = True
        elif response["status"] == "failed":
            logger.debug(f"Feed Failure - {response['pair']}")
            response["status"] = "failed"
            response["success"] = False
        else:
            return response
    return response

def stop_ws_stream(pair, tracking_number, type):
    logger.trace(f"Stop WS Ticker - {pair}")
    if pair and len(pair) > 0:
        # try:
        #     # running_count = count_running_feeds_by_pair()
        # except:
        #     logger.error(f"Exception couting feed, not critical")
        #     logger.error(traceback.format_exc())
        matched_feed = fetch_active_feed_by_tracking(tracking_number)
        response = binanceint.stop_ws_stream(pair, tracking_number, type)
        logger.trace(pformat(matched_feed))
        logger.trace(pformat(response))
        if response["success"]:
            logger.debug("Feed stopped")
            response["feed_id"] = int(matched_feed["feeds"].id)
            return response
        else:
            logger.error("Issue stopping feed")
            response["success"] = False
            response["feed_id"] = 0
            return response
    else:
        response = {"error": "invalid pair information"}
        response["feed_id"] = 0
        response["success"] = False
    return response

def process_market_data_request_event(req):
    if config["binance"]["mock"]:
        return True
    else:
        return False

def restart_state():
    running_feeds = fetch_running_feeds()
    binanceint.restart_state(running_feeds)

def emit_trade_data_event(data):
    logger.trace("Emitting trade data event")
    do_emit = True
    if do_emit:
        logger.debug("Emitting trade data")
        logger.trace(pformat(data))
        event_payload = events.BinanceTradeDataEvent(data["symbol"], data["event_type"], data)
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
        # Build failed event log here

def fetch_active_feeds():
    from sqlalchemy import select
    logger.trace("Fetch active feeds")
    session = db_session()
    try:
        session.commit()
        statement = select(models.ActiveFeedsModel)
        result = session.execute(statement).scalars().all()
        logger.trace(f"{result}")
        if len(result) > 0:
            return dict(success = True, feeds = result, error = None)
        else:
            logger.warn(f"No feeds")
            return dict(success = False, feeds = {}, error = f"No feeds")
    except Exception:
        logger.error(f"Exception fetching Entry")
        logger.error(traceback.format_exc())
        return dict(success = False, feeds = {}, error = traceback.format_exc())
    finally:
        session.close()


def fetch_active_feed(idp):
    logger.trace("Fetch active feed")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.ActiveFeedsModel).filter(models.ActiveFeedsModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"{result}")
                return dict(success = True, feeds = result, error = None)
            else:
                logger.error(f"Feed - {idp}  - not found")
                return dict(success = False, feeds = {}, error = f"Feed - {idp} - not found")
        except Exception:
            logger.error(f"Exception fetching feed")
            logger.error(traceback.format_exc())
            return dict(success = False, feeds = {}, error = traceback.format_exc())
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        session.close()
        return dict(success = False, feeds = {}, error = "No feed ID to fetch")

def fetch_active_feed_by_tracking(tracking_number):
    logger.trace("Fetch active feed")
    from sqlalchemy import select, desc
    session = db_session()
    if tracking_number:
        try:
            session.commit()
            statement = select(models.ActiveFeedsModel).filter(models.ActiveFeedsModel.tracking_number == tracking_number).order_by(desc(models.ActiveFeedsModel.id))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"{result}")
                return dict(success = True, feeds = result, error = None)
            else:
                logger.error(f"Feed - {tracking_number}  - not found")
                return dict(success = False, feeds = {}, error = f"Feed - {tracking_number} - not found")
        except Exception:
            logger.error(f"Exception fetching feed")
            logger.error(traceback.format_exc())
            return dict(success = False, feeds = {}, error = traceback.format_exc())
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        session.close()
        return dict(success = False, feeds = {}, error = "No feed ID to fetch")

def fetch_running_feeds():
    logger.trace("Fetch active feeds")
    from sqlalchemy import select
    session = db_session()
    try:
        session.commit()
        statement = select(models.ActiveFeedsModel).filter(models.ActiveFeedsModel.status == "active")
        result = session.execute(statement).scalars().all()
        logger.trace(f"{result}")
        if len(result):
            return dict(success = True, feeds = result, error = None)
        else:
            logger.warn(f"Running feeds - not found")
            return dict(success = True, feeds = {}, error = f"Running feeds not found")
    except Exception:
        logger.error(f"Exception fetching feed")
        logger.error(traceback.format_exc())
        return dict(success = False, feeds = {}, error = traceback.format_exc())
    finally:
        session.close()

def count_running_feeds_by_pair():
    logger.trace("Fetch active feeds")
    from sqlalchemy import select, func
    session = db_session()
    try:
        session.commit()
        statement = select(models.ActiveFeedsModel.pair, func.count(models.ActiveFeedsModel.status). \
                    group_by(models.ActiveFeedsModel.pair)). \
                    filter(models.ActiveFeedsModel.status == "active")
        result = session.execute(statement).scalars().all()
        if len(result):
            logger.trace(f"{result}")
            return dict(success = True, feeds = result, error = None)
        else:
            logger.error(f"Running feeds - not found")
            return dict(success = True, feeds = {}, error = f"Running feeds not found")
    except Exception:
        logger.error(f"Exception fetching feed")
        logger.error(traceback.format_exc())
        return dict(success = False, feeds = {}, error = traceback.format_exc())
    finally:
        session.close()

def update_active_feed(idp, statusp):
    logger.trace("Update entry pricing record in db")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.ActiveFeedsModel).filter(models.ActiveFeedsModel.id == int(idp))
            result = session.execute(statement).scalars().first()
            if result:
                logger.trace(f"Got - {result}")
                if statusp:
                    result.status = statusp
                session.add(result)
                session.commit()
                return dict(success = True, id = idp, error = None)
            else:
                logger.error(f"Feed - {idp}  - not found")
                return dict(success = True, id = idp, error = f"Feed - {idp} - not found")
        except Exception:
            session.rollback()
            logger.error(f"Exception fetching Feed")
            logger.error(traceback.format_exc())
            return dict(success = False, id = idp, error = traceback.format_exc())
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        session.close()
        return dict(success = False, id = idp, error = "No ID to fetch")

def create_new_active_feed(feedinfop):
    logger.debug("Persisting feed")
    logger.trace(f"{feedinfop}")
    session = db_session()
    try:
        feed = models.ActiveFeedsModel(
            tracking_number = feedinfop["tracking_number"],
            pair = feedinfop["pair"],
            status = feedinfop['status'],
            detail = json.dumps(feedinfop['detail'], cls=UUIDEncoder),
            error_information = feedinfop['error_information'],
            type = feedinfop['type'],
        )
        session.add(feed)
        session.commit()
        return dict(success = True, id = feed.id, error = None)
    except Exception:
        session.rollback()
        logger.error(traceback.format_exc())
        logger.error("Could not store feed info")
        return dict(success = False, id = 0, error = traceback.format_exc())
    finally:
        session.close()

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