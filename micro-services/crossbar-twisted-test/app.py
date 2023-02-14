#!/bin/python3

import os, sys, traceback
sys.path.append(r'./modules')

from envyaml import EnvYAML
from time import sleep
from pprint import pformat
from apicontroller import FlaskThread

from modules.logger import setup_custom_logger

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
    import logic
    apiserver = startApiServer()
    logger.info(f"Start - {config['general']['app_name']}")
    scheduling = start_schedules()
    logic.populate()
    # setup_bpm_subscriptions()
    # poll_for_new_messages()