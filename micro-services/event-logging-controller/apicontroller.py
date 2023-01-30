import os, time, json, sys
sys.path.append(r'./modules')
from envyaml import EnvYAML
from flask import jsonify, request, Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Info, Counter, Summary, Gauge, Enum
from pprint import pformat
from threading import Thread
import modules.defroutes, logic
import modules.shared_libs as shared_libs
from modules.defroutes import health_bp
from modules.database import db_session
from modules.logger import setup_custom_logger
import models
from uuid import UUID

config = EnvYAML('config.yml')
logger = setup_custom_logger(__name__)

APP_NAME = config['general']['app_name']
TOPIC_PREFIX = config['kafka']['kafka_topic_prefix']

app = Flask(__name__)
app.register_blueprint(health_bp)

# @app.teardown_appcontext
# def shutdown_session(exception=None):
#     db_session.remove()

#Prometheus Exporter
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    f"/metrics": make_wsgi_app()
})

def process_new_events():
    import string, random
    if config['kafka']['random_consumer_group']:
        letters = string.ascii_lowercase
        consumergroup = ( ''.join(random.choice(letters) for i in range(10)) )
    else:
        consumergroup = config['kafka']['logging_event_consumer_group']
    logger.debug(f"Consumer Group - {consumergroup}")
    topics = [ TOPIC_PREFIX+config['logging']['kafka_log_handler_topic']
    ]
    logger.debug(f"Consuming - {pformat(topics)}")
    logic.consume(topics,consumergroup)

@app.route("/" + APP_NAME + '/api/v1/ping')
def pingevent():
    d = {}
    d["event"] = "PING"
    return json.dumps(d)

class FlaskThread(Thread):
    def run(self):
        app.run(
            host='0.0.0.0',
            port=config['flask']['default_port'],
            debug=config['flask']['debug_enabled'],
            use_debugger=config['flask']['debug_enabled'],
            use_reloader=False)