from io import DEFAULT_BUFFER_SIZE
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

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)

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
        consumergroup = config['kafka']['trade_data_consumer_group']
    logger.debug(f"Consumer Group - {consumergroup}")
    topics = [ TOPIC_PREFIX+config['kafka']['binance_trade_data_topic']
    ]
    logger.debug(f"Consuming - {pformat(topics)}")
    logic.consume(topics, consumergroup)

@app.route("/" + APP_NAME + '/api/v1/ping')
def pingevent():
    d = {}
    d["event"] = "PING"
    return json.dumps(d)

@app.route("/" + APP_NAME + '/ws_stream', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
def ws_stream_start():
    try:
        pair = request.args.get('market')
        tracking_number = request.args.get('tracking_number')
        type = request.args.get('type')
    except:
        logger.error("Missing parameters, market, tracking_number, type is mandatory")
        return {}
    p = {}
    if pair:
        p = shared_libs.split_market_pair(pair)
    elif not pair:
        return "Pair not parseable"
    logger.debug(pformat(p))
    feedinfo = {}
    feedinfo = logic.start_ws_stream(p["condensed_lower_pair"], tracking_number, type)
    logger.debug("Feed Info!")
    logger.debug(pformat(feedinfo))
    if feedinfo["success"]:
        db_result = logic.create_new_active_feed(feedinfo)
        if db_result["success"]:
            logger.debug("feed commited")
        else:
            logger.error("Feed persistence failed")
    else:
        logger.error("Feed setup failed")
    return json.dumps(feedinfo, cls=UUIDEncoder)

@app.route("/" + APP_NAME + '/ws_stream', methods=['DELETE']) #?market=BTCUSDT, can handle slashes and lowercase
def ws_stream_stop():
    try:
        pair = request.args.get('market')
        tracking_number = request.args.get('tracking_number')
        type = request.args.get('type')
    except:
        logger.error("Missing parameters, market, tracking_number, type is mandatory")
        return {}
    p = {}
    if pair:
        p = shared_libs.split_market_pair(pair)
    elif not pair:
        return json.dumps({"error": "Pair not parseable"})
    logger.debug(pformat(p))
    feedinfo = {}
    feedinfo = logic.stop_ws_stream(p["condensed_lower_pair"], tracking_number, type)
    logger.debug("Feed Info!")
    logger.debug(pformat(feedinfo))
    if feedinfo["success"]:
        db_result = logic.update_active_feed(feedinfo["feed_id"], "inactive")
        if db_result["success"]:
            logger.debug("Feed persistence success")
        else:
            logger.error("Feed persistence failed")
        logger.debug(f"{db_result}")
        return json.dumps(feedinfo, cls=UUIDEncoder)
    else:
        logger.error("Feed teardown failed")
        return json.dumps(feedinfo, cls=UUIDEncoder)

# @app.route("/" + APP_NAME + '/signal', methods=['POST'])
# def signal_insert():
#     tracking_number = request.json.get('tracking_number', '')
#     status = request.json.get('status', '')
#     signal = SignalModel(tracking_number=tracking_number, status=status)
#     db.session.add(signal)
#     db.session.commit()
#     return signal_schema.jsonify(signal)

class FlaskThread(Thread):
    def run(self):
        app.run(
            host='0.0.0.0',
            port=config['flask']['default_port'],
            debug=config['flask']['debug_enabled'],
            use_debugger=config['flask']['debug_enabled'],
            use_reloader=False)