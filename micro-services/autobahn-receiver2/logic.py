#!/bin/python3

import sys, traceback
sys.path.append(r'./modules')

from envyaml import EnvYAML
import os
from pprint import pformat

from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.util import sleep
from autobahn.twisted.component import Component, run

from modules.logger import setup_custom_logger, printLoggers, setLevel

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

import httpimport
httpimport.CONFIG.read(config["modules"]["profile_source"])

with httpimport.remote_repo(config["modules"]["import_url"], profile=config["modules"]["import_profile"]):
  import UserSignedUp

with httpimport.remote_repo(config["modules"]["import_url"], profile=config["modules"]["import_profile"]):
  from UserSignUp import UserSignUp

PING_MINIMUM_WAIT = 1

comp = Component(
            transports=config["crossbar"]["crossbar_url"],
            realm=config["crossbar"]["crossbar_realm"]
        )

@comp.on_join
@inlineCallbacks
def joined(session, details):
    logger.debug("session ready")

    def debugging(count):
        logger.debug(count)

    try:
        yield session.subscribe(debugging, 'com.myapp.topic2')
        logger.debug("subscribed to topic")
    except Exception as e:
        logger.debug("could not subscribe to topic: {0}".format(e))

if __name__ == "__main__":
    logger.debug("Init!")
    run([comp])