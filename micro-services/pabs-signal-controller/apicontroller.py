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
    topics = [TOPIC_PREFIX+config['kafka']['signals_topic'],
            TOPIC_PREFIX+config['kafka']['binance_topic']
    ]
    logger.debug(f"Consuming - {pformat(topics)}")
    logic.consume(topics, consumergroup)

@app.route("/" + APP_NAME + '/api/v1/ping')
def pingevent():
    d = {}
    d["event"] = "PING"
    return json.dumps(d)

@app.route("/" + APP_NAME + '/signal', methods=['POST'])
def signal_insert():
    tracking_number = request.json.get('tracking_number', '')
    status = request.json.get('status', '')
    # signal = models.SignalModel(tracking_number=tracking_number, status=status)
    # db.session.add(signal)
    # db.session.commit()
    # return signal_schema.jsonify(signal)

@app.route("/" + APP_NAME + '/action_signal', methods=['GET'])
def collection_actionable_signal():
    allowed_signal = logic.fetch_allowed_signal()
    if allowed_signal:
        logger.trace(f"Fetching signal - {pformat(allowed_signal)}")
        # sigs = db.session.query(SignalModel).all()
        # if sigs and len(sigs) > 0:
        #     for sig in sigs:
        #         if sig.tracking_number == allowed_signal["tracking_number"] and sig.id == allowed_signal["id"]:
        #             return signal_schema.jsonify(sig)
    else:
        logger.trace("No signals in actionable state")
        return json.dumps({})

@app.route("/" + APP_NAME + '/ticker', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
def fetch_market_ticker():
    try:
        pair = request.args.get('market')
    except:
        pair = {}
    try:
        ticker = logic.fetch_market_ticker(pair)
        return json.dumps(ticker)
    except:
        return json.dumps({})

# @app.route("/" + APP_NAME + '/funding', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
# def check_funding():
#     try:
#         pair = request.args.get('market')
#     except:
#         pair = {}
#     try:
#         logger.trace(f"Request funding for - {pair}")
#         funding_info = logic.check_signal_funding("123", pair)
#         logger.trace(funding_info)
#         return json.dumps(funding_info)
#     except:
#         return json.dumps({})

class FlaskThread(Thread):
    def run(self):
        app.run(
            host='0.0.0.0',
            port=config['flask']['default_port'],
            debug=config['flask']['debug_enabled'],
            use_debugger=config['flask']['debug_enabled'],
            use_reloader=False)