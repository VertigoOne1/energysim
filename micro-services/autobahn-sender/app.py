#!/bin/python3

import os, sys, traceback, signal
sys.path.append(r'./modules')

from envyaml import EnvYAML

from modules.logger import setup_custom_logger

from scheduler import start_schedules

def quit_now(signum, frame):
    print("STOPPING!")
    exit(1)

signal.signal(signal.SIGINT, quit_now)

signal.signal(signal.SIGTERM, quit_now)

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

if __name__ == '__main__':
    import logic
    logger.info(f"Start - {config['general']['app_name']}")
    scheduling = start_schedules()
    logic.run([logic.comp])