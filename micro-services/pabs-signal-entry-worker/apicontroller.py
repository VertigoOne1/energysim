import os, time, json, sys
sys.path.append(r'./modules')
from flask import jsonify, request, Flask
from envyaml import EnvYAML
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from datetime import datetime, timezone
from prometheus_client import make_wsgi_app
from pprint import pformat
from threading import Thread
import logic
from modules.defroutes import health_bp
from modules.database import db_session
from modules.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

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
        consumergroup = config['kafka']['signal_controller_consumer_group']
    logger.debug(f"Consumer Group - {consumergroup}")
    topics = [ TOPIC_PREFIX+config['kafka']['binance_topic'],
            TOPIC_PREFIX+config['kafka']['binance_trade_data_topic'],
            # TOPIC_PREFIX+config['kafka']['binance_market_data_topic'],
            # TOPIC_PREFIX+config['kafka']['signals_topic'],
    ]
    logger.debug(f"Consuming - {pformat(topics)}")
    # logic.process_signals()
    logic.consume2(topics, consumergroup)

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