#!/bin/python3

import sys
sys.path.append(r'./modules')

from envyaml import EnvYAML
from time import sleep
from pprint import pformat
import modules.defconfig
from modules.logger import setup_custom_logger
from apicontroller import process_new_events, FlaskThread
from scheduler import start_schedules

logger = setup_custom_logger(__name__)
config = EnvYAML('config.yml')

def startApiServer():
    server = FlaskThread()
    server.daemon = True
    server.start()

if __name__ == '__main__':
    apiserver = startApiServer()
    logger.info(f"Start - {config['general']['app_name']}")
    scheduling = start_schedules()
    process_new_events()
    logger.info(f"Stop - {config['general']['app_name']}")