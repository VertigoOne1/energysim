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
  import UserSignUp

CYCLE_DEFUALT_WAIT_MS = 1000

comp = Component(
            transports=config["crossbar"]["crossbar_url"],
            realm=config["crossbar"]["crossbar_realm"]
        )

@comp.on_join
@inlineCallbacks
def joined(session, details):
    logger.debug("session ready")

    counter = 0
    while True:
        logger.debug("Looping")
        # publish() only returns a Deferred if we asked for an acknowledgement
        session.publish('com.myapp.topic1', counter)
        session.publish('com.myapp.topic2', counter+1000)
        counter += 1
        yield sleep(1)

if __name__ == "__main__":
    logger.debug("Init!")
    run([comp])