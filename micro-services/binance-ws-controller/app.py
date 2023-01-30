#!/bin/python3

import sys, os
sys.path.append(r'./modules')

from envyaml import EnvYAML
from time import sleep
from pprint import pformat
import modules.defconfig
from modules.logger import setup_custom_logger
from bpm_handlers import setup_bpm_subscriptions
from apicontroller import process_new_events, FlaskThread
from logic import restart_state
from scheduler import start_schedules

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

def startApiServer():
    server = FlaskThread()
    server.daemon = True
    server.start()

if __name__ == '__main__':
    apiserver = startApiServer()
    logger.info(f"Start - {config['general']['app_name']}")
    scheduling = start_schedules()
    setup_bpm_subscriptions()
    restart_state()
    process_new_events()
    logger.info(f"Stop - {config['general']['app_name']}")