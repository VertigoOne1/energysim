#!/bin/python3

from curses import savetty
import sys, traceback
sys.path.append(r'./modules')

import json, requests, socket, time, re
from envyaml import EnvYAML
import os, fnmatch
from pprint import pformat
from random import randint
import modules.defconfig as defconfig, modules.eventbus as eventbus, apicontroller
import metrics, models
import modules.shared_libs as shared_libs, modules.events as events
from modules.logger import setup_custom_logger
from modules.database import db_session

logger = setup_custom_logger(__name__)
config = EnvYAML('config.yml')

BROKER_URL = config['kafka']['broker_url']
TOPIC_PREFIX = config['kafka']['kafka_topic_prefix']

PING_MINIMUM_WAIT = 1

def consume(topic, group):
    from kafka import KafkaConsumer
    from marshmallow import ValidationError
    consumer = KafkaConsumer(group_id=group,
                            bootstrap_servers=BROKER_URL,
                            auto_offset_reset=config["kafka"]["auto_offset_reset"], enable_auto_commit=True,
                            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
    consumer.subscribe(topic)
    for message in consumer:
        data = message.value
        metrics.p_logging_events_consumed.inc()
        logger.info(pformat(data))
        store_logging_message("NA",data)
        # event_schema = events.EventSchema()
        # event = {}
        # raw_msg = ""
        # try:
        #     event = event_schema.loads(data)
        # except ValidationError as err:
        #     logger.debug(err.messages)
        #     logger.debug(err.valid_data)
        #     logger.warn("Malformed event skipped")
        # if event:
        #     logger.debug(pformat(event))
        #     try:
        #         if event["etype"] == events.EventTypes.PABS_RAW_MESSAGE.value:
        #             raw_schema = events.PabsRawMessageEventSchema()
        #             try:
        #                 raw_msg = raw_schema.loads(json.dumps(event["payload"]))
        #                 logger.debug(pformat(raw_msg))
        #                 if process_raw_message(raw_msg):
        #                     logger.debug("Update message processed")
        #                 else:
        #                     logger.debug("Message ignored")
        #             except ValidationError as err:
        #                 logger.debug(err.messages)
        #                 logger.debug(err.valid_data)
        #                 logger.warn("Malformed payload skipped")
        #                 p_payload_validation_errors.inc()
        #         else:
        #             logger.warn("Event not raw message type")
        #     except KeyError as err:
        #         logger.error(pformat(err))
        #         time.sleep(5)

def process_logging_message(msg):
    logger.trace("New logging message detected")

def store_logging_message(level, raw_message):
    session = db_session()
    try:
        message = models.LoggingEventModel(level=level, message=raw_message)
        session.add(message)
        session.commit()
    except Exception:
        logger.error(f"Exception with keep alive")
        session.rollback()
        logger.error(traceback.format_exc())
    finally:
        session.close()
    metrics.p_logging_events_stored.inc()

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