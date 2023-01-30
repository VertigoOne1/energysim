import os, time, json, sys
sys.path.append(r'./modules')
from envyaml import EnvYAML
from flask import jsonify, request, Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Info, Counter, Summary, Gauge, Enum
from datetime import datetime, timezone
from pprint import pformat
from threading import Thread
import modules.defroutes, logic, binance
import modules.shared_libs as shared_libs, modules.bpm as bpm
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
    topics = [ TOPIC_PREFIX+config['kafka']['binance_topic' ]
    ]
    logger.debug(f"Consuming - {pformat(topics)}")
    logic.consume(topics, consumergroup)

@app.route("/" + APP_NAME + '/api/v1/ping')
def pingevent():
    d = {}
    d["event"] = "PING"
    return json.dumps(d)

@app.route("/" + APP_NAME + '/operatingMode', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
def operatingMode():
    res = {}
    if config["binance"]["mock"]:
        logger.warn("Binance trading is MOCK")
        res["mode"] = "mock"
    else:
        res["mode"] = "live"
        logger.warn("Binance trading is LIVE")
    if config["binance"]["sandbox"]:
        res["mode"] = "sandbox"
    return json.dumps(res)

@app.route("/" + APP_NAME + '/ticker', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
def fetch_market_ticker():
    try:
        pair = request.args.get('market')
        logger.trace(pair)
    except:
        pair = {}
    p = {}
    if pair and "/" in pair:
        p = shared_libs.split_market_pair(pair)
    elif not pair:
        return "NO PAIR SPECIFIED, did you forget ?market=BTCUSDT"
    else:
        p["condensed_pair"] = pair
    logger.trace(pformat(p))
    ticker = dict()
    try:
        ticker = binance.fetch_ticker(p["condensed_pair"].upper())
        logger.debug(pformat(ticker))
    except Exception as e:
        logger.error("Issue with fetch_ticker")
        logger.error(e, exc_info=True)
    return json.dumps(ticker)

@app.route("/" + APP_NAME + '/market', methods=['GET']) #?market=BTCUSDT, can handle slashes and lowercase
def fetch_market():
    logger.debug("Fetch market api hit")
    try:
        pair = request.args.get('market')
        logger.trace(pair)
    except:
        pair = {}
    p = {}
    if pair and "/" in pair:
        p = shared_libs.split_market_pair(pair)
    elif not pair:
        return "NO PAIR SPECIFIED, did you forget ?market=BTCUSDT"
    else:
        p["condensed_pair"] = pair
    logger.trace(pformat(p))
    market = dict()
    try:
        market = binance.fetch_pair_market(p["condensed_pair"].upper())
        logger.debug(pformat(market))
        logger.debug("Returning market data to caller")
        return json.dumps(market)
    except Exception as e:
        logger.error("Issue with fetch_market")
        logger.error(e, exc_info=True)
        market = {}
        return json.dumps(market)

@app.route("/" + APP_NAME + '/wallet', methods=['GET'])
def fetch_wallet():
    wallet = {}
    try:
        wallet = binance.fetch_wallet_information()
        logic.store_wallet_information(wallet)
    except Exception as e:
        logger.error("Issue with fetch_wallet_information")
        logger.error(e, exc_info=True)
    return json.dumps(wallet)

## Market orders don't need to be polled, only checked if complete
@app.route("/" + APP_NAME + '/market_buy_order', methods=['POST'])
def api_create_market_buy_order():
    logger.trace(pformat(request.json))
    tracking_number = request.json.get('tracking_number', '')
    market = shared_libs.split_market_pair(request.json.get('market', ''))["condensed_upper_pair"]
    qty = request.json.get('qty', '')
    price = request.json.get('price', '')
    order_type = request.json.get('order_type', '')
    origin_process_id = request.json.get('origin_process_id', '')
    logger.debug("Buy Order received")
    if tracking_number and request.json.get('market', '') and request.json.get('order_type', ''):
        logger.debug("Enough info to start the process")
        bpm.start_process("BinanceOrderProcess", {"market":market, "qty": qty, "price": price, "order_type": order_type, "tracking_number": tracking_number, "origin_process_id": origin_process_id}, business_key = tracking_number)
        logger.debug(f"API - api_create_market_buy_order|{tracking_number}|{market}|{qty}|{price}|{order_type}|{origin_process_id}")
        return json.dumps({"status": "process started"})
    else:
        logger.error("Insufficient information to start an order process")
        return json.dumps({"status": "failed"})

## Market orders don't need to be polled, only checked if complete
@app.route("/" + APP_NAME + '/market_sell_order', methods=['POST'])
def api_create_market_sell_order():
    logger.trace(pformat(request.json))
    tracking_number = request.json.get('tracking_number', '')
    market = shared_libs.split_market_pair(request.json.get('market', ''))["condensed_upper_pair"]
    qty = request.json.get('qty', '')
    price = request.json.get('price', '')
    order_type = request.json.get('order_type', '')
    origin_process_id = request.json.get('origin_process_id', '')
    logger.debug(f"Sell Order received - order_type - {order_type} - qty - {qty} - price {price}")
    if tracking_number and request.json.get('market', '') and request.json.get('order_type', ''):
        logger.debug("Enough info to start the process")
        bpm.start_process("BinanceOrderProcess", {"market":market, "qty": qty, "price": price, "order_type": order_type, "tracking_number": tracking_number, "origin_process_id": origin_process_id}, business_key = tracking_number)
        logger.debug(f"API - api_create_market_buy_order|{tracking_number}|{market}|{qty}|{price}|{order_type}|{origin_process_id}")
        return json.dumps({"status": "process started"})
    else:
        logger.error("Insufficient information to start an order process")
        return json.dumps({"status": "failed"})

## Limit orders need to be polled to check their status and completion
@app.route("/" + APP_NAME + '/limit_order', methods=['POST'])
def api_create_limit_buy_order():
    tracking_number = request.json.get('tracking_number', '')
    market = request.json.get('market', '')
    qty = request.json.get('qty', '')
    price = request.json.get('price', '')
    order_type = request.json.get('order_type', '')
    logger.trace(f"API - create_api_market_buy_order|{tracking_number}|{market}|{qty}|{price}|{order_type}")
    result = binance.create_limit_buy_order(tracking_number, market, qty, price)
    return json.dumps(result)

# CONTINUE HERE WITH ORDER CREATE AND SUCH, AND MOVE THE DIRECT BINANCE ACCESS FROM API CONTROLLER TO LOGIC

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