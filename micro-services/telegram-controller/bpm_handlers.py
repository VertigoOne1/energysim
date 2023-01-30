#!/bin/python3

import os, sys, traceback
sys.path.append(r'./modules')

from envyaml import EnvYAML
from pprint import pformat
from datetime import datetime, timezone
from random import randint

from modules.logger import setup_custom_logger

from concurrent.futures.thread import ThreadPoolExecutor
from modules.camunda.external_task.external_task_worker import ExternalTaskWorker

from modules.camunda.external_task.external_task import ExternalTask

import modules.bpm as bpm
import logic

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

def setup_bpm_subscriptions():
    logger.debug("Set up subscriptions")
    topics = [
        ("A3ProcessRawMessage", handle_ProcessRawMessage),
        ("A3EmitRawMessage", handle_EmitRawMessage),
        ("A3RequeueRawMessage", handle_RequeueRawMessage),
        ("A3EmitRequeueMessage", handle_EmitRequeueMessage)
    ]
    executor = ThreadPoolExecutor(max_workers=len(topics))
    for index, topic_handler in enumerate(topics):
        topic = topic_handler[0]
        handler_func = topic_handler[1]
        executor.submit(ExternalTaskWorker(worker_id=index, config=bpm.default_bpm_config).subscribe, topic, handler_func)
        logger.debug(f"subscribed - {topic}")
        time.sleep(0.17)


def handle_ProcessRawMessage(task: ExternalTask):
    result = {}
    logger.trace(f"handle_ProcessRawMessage - {task.get_summary()}")

    vars = task.get_variables()
    logger.trace(f"Message ID: {vars['message_id']}")

    logger.info(f"Nothing to do here (yet)")
    result["status"] = "passed"

    if result["status"] == "passed":
        return task.complete(result)
    else:
        return task.bpmn_error("501", "testing exception handling", {"exception": "test test", "failed_message": logic.fetch_msg(vars['message_id']) })

def handle_EmitRawMessage(task: ExternalTask):
    result = {}
    logger.trace(f"handle_EmitRawMessage - {task.get_summary()}")
    vars = task.get_variables()
    logger.info(f"Message ID: {vars['message_id']}")

    if not vars['message_id']:
        return task.bpmn_error("502", "No message id from processing", {})

    try:
        logger.debug("Fetching message from DB")
        msg = logic.fetch_msg(vars['message_id'])
        logger.debug(msg)
    except:
        logger.error("No message")
        msg = ""
    if msg:
        try:
            if config['general']['emit_enabled']:
                logic.emit_raw_message_event(msg['message'])
                logger.debug("Emitted message")
                result["status"] = "passed"
            else:
                logger.info("Emit is disabled in config")
                result["status"] = "passed"
            return task.complete(result)
        except Exception:
            logger.error(f"Exception emitting msg")
            logger.error(traceback.format_exc())
            return task.bpmn_error("502", "exception emitting msg", {"exception": traceback.format_exc()})
    else:
        return task.bpmn_error("502", "no msg to emit", {"exception": ""})

def handle_EmitRequeueMessage(task: ExternalTask):
    result = {}
    logger.trace(f"handle_EmitRequeueMessage - {task.get_summary()}")
    vars = task.get_variables()
    logger.info(f"Message ID: {vars['message_id']}")

    try:
        logger.debug("fetch requeue message")
        msg = vars['requeue_message']
    except:
        logger.debug("No requeue_message")
        msg = ""
    if msg:
        try:
            if config['general']['emit_enabled']:
                logic.emit_raw_message_event(msg['message'])
                logger.debug("Emitted requeue message")
                result["status"] = "passed"
            else:
                logger.info("Emit is disabled in config")
                result["status"] = "passed"
            return task.complete(result)
        except Exception:
            logger.error(f"Exception emitting requeue msg")
            logger.error(traceback.format_exc())
            return task.bpmn_error("502", "exception requeue emitting msg", {"exception": traceback.format_exc()})
    else:
        return task.bpmn_error("502", "no msg to emit", {"exception": ""})

def handle_RequeueRawMessage(task: ExternalTask):
    result = {}
    logger.trace(f"handle_RequeueRawMessage - {task.get_summary()}")
    vars = task.get_variables()
    try:
        result["requeue_message"] = vars['requeue_message']
        return task.complete(result)
    except Exception:
        logger.error(f"Exception emitting msg")
        logger.error(traceback.format_exc())
        return task.bpmn_error("503", "Exception", {"exception": traceback.format_exc()})