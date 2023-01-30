#!/bin/python3

import sys
sys.path.append(r'./modules')

import json
from kafka import KafkaProducer, KafkaConsumer
import os, fnmatch, logging, datetime, traceback
from pprint import pformat
from envyaml import EnvYAML

if "CONFIG_FILE" in os.environ:
    logging.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logging.info("Loading Development Config")
    config = EnvYAML('config.yml')

BROKER_URL = config['kafka']['broker_url']
TOPIC_PREFIX = config['kafka']['kafka_topic_prefix']

# logger = logger.setup_custom_logger(__name__)

producer = KafkaProducer(bootstrap_servers=BROKER_URL, value_serializer=lambda x:json.dumps(x).encode('utf-8'))

class KafkaLoggingHandler(logging.Handler):

    topic = TOPIC_PREFIX+config["logging"]["kafka_log_handler_topic"]

    def __init__(self):
        logging.Handler.__init__(self)
        self.producer = KafkaProducer(bootstrap_servers=BROKER_URL, value_serializer=lambda x:json.dumps(x).encode('utf-8'))

    def emit(self, record):
        #drop kafka logging to avoid infinite recursion
        if record.name == 'kafka':
            return

        created = datetime.datetime.fromtimestamp(record.created)
        if len(record.args) > 0:
            obj = {
                "level": record.levelname.lower(),
                'name' : f"{record.name}",
                'funcName': f"{record.funcName}",
                "msg": f"{record.msg}" % f"{record.args},",
                "source": "%s:%d" % (record.filename, record.lineno),
                "time": f"{created}",
            }
        else:
            obj = {
                "level": record.levelname.lower(),
                'name' : f"{record.name}",
                'funcName': f"{record.funcName}",
                "msg": f"{record.msg}",
                "source": "%s:%d" % (record.filename, record.lineno),
                "time": f"{created}",
            }
        if record.exc_info is not None:
            obj["exception"] = traceback.format_exception(*record.exc_info)[1:]
        obj["service"] = f"{config['general']['app_name']}"

        try:
            msg = json.loads(json.dumps(obj, sort_keys=True, skipkeys=True))
            producer.send(self.topic,value=msg)
        except:
            ei = sys.exc_info()
            traceback.print_exception(ei[0], ei[1], ei[2], None, sys.stderr)
            del ei

    def close(self):
        self.producer = None
        logging.Handler.close(self)

def emit(topic, msg):
    try:
        producer.send(topic,value=msg)
    except:
        import traceback
        ei = sys.exc_info()
        traceback.print_exception(ei[0], ei[1], ei[2], None, sys.stderr)
        del ei