#!/bin/python3

import sys, traceback
sys.path.append(r'./modules')

from envyaml import EnvYAML
import os
from pprint import pformat
from random import randint
import apicontroller as apicontroller
# import modules.shared_libs as shared_libs

from modules.logger import setup_custom_logger
import models, metrics

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

PING_MINIMUM_WAIT = 1

def populate():
    mod = models.UserProfile(username="marnus")
    print(mod)
    print(mod.dict())
    print(mod.json())

# def give_emoji_free_text(text):
#     return emoji.demojize(text, delimiters=(":", ":"))

# def emit_raw_message_event(message):
#     try:
#         event_payload = eventdef.Albert3RawMessageEvent(message)
#         logger.trace(pformat(event_payload))
#         payload_schema = eventdef.Albert3RawMessageEventSchema()
#         payload = payload_schema.dump(event_payload)
#         logger.debug(pformat(payload))
#         event_base = eventdef.Event(eventdef.EventTypes.ALBERT3_RAW_MESSAGE.value,payload)
#         base_schema = eventdef.EventSchema()
#         logger.trace(pformat(event_base))
#         metrics.a3_messages_success.inc()
#         try:
#             eventbus.emit(TOPIC_PREFIX+config['kafka']['raw_messages_topic'],base_schema.dumps(event_base))
#             metrics.a3_events_emitted.inc()
#         except Exception:
#             logger.error(traceback.format_exc())
#             logger.error("Issue emiting event, broker down?")
#     except Exception:
#         logger.error(traceback.format_exc())
#         logger.error("Issue emiting event, broker down?")