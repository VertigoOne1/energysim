#!/bin/python3

## NOT USED

import os
import ccxt, sys, json, time, re, math, traceback
from random import randint
from tenacity import *
from datetime import datetime, timedelta
from pprint import pformat
import envyaml
from modules.logger import setup_custom_logger
from envyaml import EnvYAML
from prometheus_client import Counter, Summary, Gauge, Enum, Info

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

exchange = "Mocked"

@retry(wait=wait_random_exponential(multiplier=1, max=60, min=20),reraise=True, stop=stop_after_attempt(60))
def fetch_ticker(pair):
    ticker = {}
    ticker["pair"] = pair
    ticker["price"] = 0.1
    return ticker