#!/bin/python3

import sys, traceback, os
sys.path.append(r'./modules')

from envyaml import EnvYAML
from pprint import pformat
from datetime import datetime, timezone
from random import randint

from modules.logger import setup_custom_logger

from concurrent.futures.thread import ThreadPoolExecutor
from modules.camunda.external_task.external_task_worker import ExternalTaskWorker

from modules.camunda.external_task.external_task import ExternalTask
from modules.camunda.process_definition.process_definition_client import ProcessDefinitionClient

import modules.bpm as bpm, modules.shared_libs as shared_libs
import logic, metrics

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
        # ("SignalAcceptance", handle_SignalAcceptance)
        # ("SignalValidation", handle_SignalValidation),
        # ("SignalDuplicateCheck", handle_SignalDuplicateCheck),
        # ("CreateNewSignal", handle_CreateNewSignal),
        # ("EmitNewSignalEvent", handle_EmitNewSignalEvent),
        # ("ExistingSignalReset", handle_EmitRequeueMessage),
        # ("EmitResetSignalEvent", handle_EmitResetSignalEvent),
    ]
    if topics:
        executor = ThreadPoolExecutor(max_workers=len(topics))
        for index, topic_handler in enumerate(topics):
            topic = topic_handler[0]
            handler_func = topic_handler[1]
            executor.submit(ExternalTaskWorker(worker_id=index, config=bpm.default_bpm_config).subscribe, topic, handler_func)
            logger.debug(f"subscribed - {topic}")
        time.sleep(0.17)
    else:
        logger.info("No topics to subscribe to")