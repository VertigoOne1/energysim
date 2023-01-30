#!/bin/python3

import sys, traceback
sys.path.append(r'./modules')

import json, requests, socket
from envyaml import EnvYAML
import os, fnmatch, time
from pprint import pformat
from random import randint
from datetime import datetime, timezone
import modules.defconfig as defconfig
import modules.eventbus as eventbus, modules.events as eventdef, apicontroller as apicontroller, modules.shared_libs as shared_libs

from telethon import TelegramClient, events, sync
from telethon.sessions import StringSession

from modules.database import db_session
from modules.logger import setup_custom_logger
import models, metrics, emoji

from modules.camunda.external_task.external_task import ExternalTask
import modules.bpm as bpm

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

PING_MINIMUM_WAIT = 1
TOPIC_PREFIX = config["kafka"]["kafka_topic_prefix"]

api_id = config['telegram']['api_id']
api_hash = config['telegram']['api_hash']
string_sesion = StringSession(config['telegram']['string_session'])

def give_emoji_free_text(text):
    return emoji.demojize(text, delimiters=(":", ":"))

def poll_for_new_messages():
    logger.info("Starting Telethon Interface")
    channel_matrix = []
    with TelegramClient(string_sesion, api_id, api_hash, auto_reconnect=True,
        request_retries=config['telegram']['request_retries'],
        connection_retries=config['telegram']['connection_retries'],
        retry_delay=config['telegram']['retry_delay'],
        timeout=config['telegram']['timeout']) as client:
        dialogs = client.get_dialogs()
        ids_to_subscribe = []
        for chat in (config['telegram']['watched_chats']):
            channel = {}
            logger.debug(f"Finding - {chat}")
            channel['chat'] = chat
            entity = client.get_entity(chat)
            if entity:
                logger.debug(f'Matched - {entity}')
                channel['channel_id'] = entity.id
                channel['title'] = entity.title
                ids_to_subscribe.append(entity.id)
                channel_matrix.append(channel)
                logger.debug(f"Entity ID - {entity.id}")
                logger.info(f"Subscribing - {entity.title}")
            else:
                logger.error("Could not find entity to subscribe to")
                logger.debug(dialogs)
        logger.debug(f"IDs ready to subscribe - {ids_to_subscribe}")
        logger.debug(f"Matrix - {channel_matrix}")
        if len(ids_to_subscribe) > 0:
            @client.on(events.NewMessage(chats=ids_to_subscribe))
            async def check_feed(event):
                metrics.telegram_messages_received.inc()
                message = give_emoji_free_text(event.raw_text) # convert emojis to words
                logger.debug(f"Event - {event}")
                ## Looking for the chat id, and topic name, then i can build a classifier in the BPM
                logger.debug(f"Message from - {event.peer_id}")
                logger.debug(f"Channel ID - {event.peer_id.channel_id}")
                t = "NA"
                id = "NA"
                logger.debug(f"Matrix - {channel_matrix}")
                for i in channel_matrix:
                    if i['channel_id'] == event.peer_id.channel_id:
                        logger.debug("Matched to watched_chats")
                        logger.debug(i['title'])
                        t = i['title']
                        id = i['channel_id']
                        break
                msg_id = store_msg(message.encode('ascii', 'xmlcharrefreplace'), id, give_emoji_free_text(t).encode('ascii', 'xmlcharrefreplace'))
                logger.debug(message)
                logger.debug(f"Added message to database - {msg_id}")
                if config['general']['bpm_enabled']:
                    try:
                        bpm.start_process("TelegramAlbert3RawMessageProcess", {"message_id": msg_id, "message_source": "telegram"}, business_key=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
                        metrics.telegram_processes_started.inc()
                    except Exception:
                        metrics.telegram_exceptions_triggered.inc()
                        logger.error(traceback.format_exc())
                        logger.error("Issue starting process")
                else:
                    logger.info("BPM disabled in config")
                    logger.debug("Would have started process - TelegramAlbert3RawMessageProcess")
            client.run_until_disconnected()
        else:
            logger.error("Not doing anything - sleep 10")
            while True:
                time.sleep(10)

def emit_raw_message_event(message):
    try:
        event_payload = eventdef.Albert3RawMessageEvent(message)
        logger.trace(pformat(event_payload))
        payload_schema = eventdef.Albert3RawMessageEventSchema()
        payload = payload_schema.dump(event_payload)
        logger.debug(pformat(payload))
        event_base = eventdef.Event(eventdef.EventTypes.ALBERT3_RAW_MESSAGE.value,payload)
        base_schema = eventdef.EventSchema()
        logger.trace(pformat(event_base))
        metrics.a3_messages_success.inc()
        try:
            eventbus.emit(TOPIC_PREFIX+config['kafka']['raw_messages_topic'],base_schema.dumps(event_base))
            metrics.a3_events_emitted.inc()
        except Exception:
            logger.error(traceback.format_exc())
            logger.error("Issue emiting event, broker down?")
    except Exception:
        logger.error(traceback.format_exc())
        logger.error("Issue emiting event, broker down?")

def fetch_msg(idp):
    logger.debug(f"Fetching msg - {idp}")
    from sqlalchemy import select
    session = db_session()
    if idp:
        try:
            session.commit()
            statement = select(models.FileMessageModel).filter(models.FileMessageModel.id == int(idp))
            result = shared_libs.row2dict(session.execute(statement).scalars().first())
            if result:
                logger.debug(pformat(result))
                return result
            else:
                logger.error(f"Message - {idp} - not found")
                return {}
        except Exception:
            logger.error(f"Exception querying data")
            logger.error(traceback.format_exc())
            return {}
        finally:
            session.close()
    else:
        logger.error("No ID to fetch")
        return {}

def store_msg(raw_message, id, t):
    from datetime import datetime
    message_entry = models.FileMessageModel(message=raw_message, chat_id=id, topic_name=t, insert_date=datetime.now())
    session = db_session()
    try:
        session.add(message_entry)
        session.commit()
        msg_id = message_entry.id
    except Exception:
        logger.error(f"Exception storing message")
        session.rollback()
        logger.error(traceback.format_exc())
        msg_id = 0
    finally:
        session.close()
    logger.debug(f"Msg ID added - {msg_id}")
    logger.debug(f"Added message to database - {msg_id}")
    return msg_id

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