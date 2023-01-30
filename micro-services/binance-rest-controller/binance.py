#!/bin/python3
import os, sys, traceback
import ccxt, json, time, re, math
from random import randint
from tenacity import *
from datetime import datetime, timedelta
from pprint import pformat
import envyaml
from modules.logger import setup_custom_logger
from envyaml import EnvYAML
from prometheus_client import Counter, Summary, Gauge, Enum, Info
import metrics, models, logic

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

if config['binance']['sandbox']:
    exchange = ccxt.binance({
        'apiKey': config['binance']['sandbox_apikey'],
        'secret': config['binance']['sandbox_secret'],
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
elif not config['binance']['sandbox']:
    exchange = ccxt.binance({
        'apiKey': config['binance']['live_apikey'],
        'secret': config['binance']['live_secret'],
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(False)

@retry(wait=wait_random_exponential(multiplier=1, max=30, min=5),reraise=True, stop=stop_after_attempt(20))
def fetch_ticker(pair):
    logger.debug(f"Fetch Ticker - {pair}")
    if pair and len(pair) > 0:
        r = dict()
        try:
            r = exchange.fetchTicker(pair)
            metrics.p_ticker_requests.inc()
        except Exception as e:
            logger.error(f"exception retrieving ticker information for {pair}, retry active")
            logger.error(e, exc_info=True)
            metrics.p_ticker_failed.inc()
    else:
        r = dict()
    if r:
        ticker = models.Ticker(True,r["symbol"],r["info"],r["timestamp"],r["datetime"],r["high"],r["low"],r["bid"],r["ask"],r["open"],r["close"],r["last"])
        return ticker.__dict__
    else:
        ticker = models.Ticker()
        return ticker.__dict__


## This fetches the wallet information
@retry(wait=wait_random_exponential(multiplier=1, max=60, min=5),reraise=True, stop=stop_after_attempt(20))
def fetch_wallet_information():
    balances = {}
    try:
        balances = exchange.fetch_balance()
        # logger.trace(pformat(balances))
        logger.debug("Received balance information from binance")
        metrics.p_wallet_requests.inc()
    except Exception as e:
        logger.error(f"exception retrieving wallet information, retry active")
        logger.error(e, exc_info=True)
        metrics.p_wallet_failed.inc()
    return balances

@retry(wait=wait_random_exponential(multiplier=1, max=60, min=5),reraise=True, stop=stop_after_attempt(20))
def fetch_pair_market(pair):
    try:
        market = exchange.market(pair)
        logger.debug(f"Retrieved market information for {pair}")
        metrics.p_market_requests.inc()
        logger.debug(f"{market}")
        return market
    except Exception as e:
        logger.error(f"exception retrieving market information for {pair}, retry active")
        logger.error(e, exc_info=True)
        metrics.p_market_failed.inc()
        market = {}
        return market

##  Cancels an order
##  NOT USED - Repurpose and correct it
# @retry(wait=wait_random_exponential(multiplier=1, max=60, min=10),reraise=True, stop=stop_after_attempt(60))
# def cancel_buy_order(exchange, signal):
#     logger.info(f"Cancelling buy order - {signal['buy_order']['id']}")
#     if config["binance"]["mock"] == False:
#         order = exchange.cancel_order(signal["buy_order"]["id"], signal["pair"])
#     else:
#         logger.info("MOCK ACTIVE - NOT CANCELLING BUY ORDER")
#         logger.info(pformat(signal))
#     return order

## Creates a market buy order, an order for a qty at market price
# @retry(wait=wait_random_exponential(multiplier=1, max=60, min=10),reraise=True, stop=stop_after_attempt(60))
def create_market_buy_order(tracking_number, pair, qty, price):
    markets = exchange.load_markets()
    logger.info(f"create market buy order - {tracking_number} - {pair} - {qty} - {price}")
    buy_order = {}
    buy_order["current_market"] = fetch_ticker(pair)
    buy_order["tracking_number"] = tracking_number
    buy_order["qty"] = exchange.amount_to_precision(pair, qty)
    buy_order["pair"] = pair
    # buy_order["price"] = exchange.price_to_precision(pair, price)
    buy_order["price"] = None
    buy_order["order_type"] = 'market'
    buy_order["side"] = 'buy'
    buy_order["params"] = {}
    buy_order["status"] = "init"
    buy_order["result"] = {}
    buy_order["order_data"] = {}
    buy_order["error_information"] = ""
    if not config["binance"]["mock"]:
        try:
            order = exchange.create_order(buy_order["pair"], buy_order["order_type"], buy_order["side"], buy_order["qty"],
            buy_order["price"], buy_order["params"])
            buy_order["status"] = "passed"
            buy_order["success"] = True
            buy_order["result"] = "completed"
            buy_order["order_data"] = {}
            # buy_order["order_data"]["id"] = 123
            buy_order["order_data"] = order
            buy_order['order_id'] = buy_order["order_data"]["id"]
            logger.info("order created")
            logger.info(pformat(buy_order))
            metrics.p_order_buy_requests.inc()
            logger.debug(f"{order}")
        except Exception as e:
            logger.error("exception creating market order")
            logger.error(e, exc_info=True)
            buy_order["status"] = "failed"
            buy_order["success"] = False
            buy_order["result"] = pformat(e)
            buy_order["error_information"] = "exception creating market order"
            metrics.p_order_buy_failed.inc()
    elif config["binance"]["mock"]:
        try:
            # order = exchange.create_order(buy_order["pair"], buy_order["order_type"], buy_order["side"], buy_order["qty"],
            # buy_order["price"], buy_order["params"])
            buy_order["status"] = "passed"
            buy_order["success"] = True
            buy_order["result"] = "config mock"
            buy_order["order_data"] = {}
            buy_order["order_data"]["id"] = 123
            buy_order['order_id'] = buy_order["order_data"]["id"]
            buy_order['order_data']["symbol"] = pair
            buy_order['order_data']["price"] = price
            buy_order['order_data']["amount"] = qty
            buy_order['order_data']["filled"] = qty
            buy_order['order_data']["status"] = "closed"
            # buy_order["order_data"] = order
            logger.info("Mocked Market buy order created")
            logger.info(pformat(buy_order))
            metrics.p_order_buy_requests.inc()
        except Exception as e:
            logger.error("exception creating market order")
            logger.error(e, exc_info=True)
            buy_order["status"] = "failed"
            buy_order["success"] = False
            buy_order["result"] = pformat(e)
            buy_order["error_information"] = "exception creating mock market order"
            metrics.p_order_buy_failed.inc()
    logger.trace("Market order result - ")
    logger.trace(pformat(buy_order))
    return buy_order

## Creates sell order at the current market price
# @retry(wait=wait_random_exponential(multiplier=1, max=60, min=10),reraise=True, stop=stop_after_attempt(60))
def create_market_sell_order(tracking_number, pair, qty, price):
    markets = exchange.load_markets()
    logger.info(f"create market sale order - {tracking_number} - {pair} - {qty} - expected price - {price}")
    sell_order = {}
    sell_order["tracking_number"] = tracking_number
    sell_order["qty"] = exchange.amount_to_precision(pair, qty)
    sell_order["pair"] = pair
    sell_order["price"] = None
    #sell_order["price"] = exchange.price_to_precision(pair, price)
    sell_order["order_type"] = 'market'
    sell_order["side"] = 'sell'
    sell_order["params"] = {}
    sell_order["current_market"] = fetch_ticker(pair)
    sell_order["status"] = "init"
    sell_order["result"] = {}
    sell_order["order_data"] = {}
    sell_order["error_information"] = ""
    if not config["binance"]["mock"]:
        try:
            order = exchange.create_order(sell_order["pair"], sell_order["order_type"], sell_order["side"], sell_order["qty"], sell_order["price"], sell_order["params"])
            sell_order["status"] = "passed"
            sell_order["result"] = "completed"
            # sell_order["order_data"] = {}
            # sell_order["order_data"]["id"] = 123
            sell_order["order_data"] = order
            sell_order['order_id'] = sell_order["order_data"]["id"]
            logger.info("Market sale order created")
            logger.info(pformat(sell_order))
            metrics.p_order_sell_requests.inc()
        except Exception as e:
            logger.error("exception creating market order")
            logger.error(e, exc_info=True)
            sell_order["status"] = "failed"
            sell_order["result"] = pformat(e)
            sell_order["error_information"] = "exception creating market sale order"
            metrics.p_order_buy_failed.inc()
    elif config["binance"]["mock"]:
        try:
            # order = exchange.create_order(sell_order["pair"], sell_order["order_type"], sell_order["side"], sell_order["qty"],
            # sell_order["price"], sell_order["params"])
            sell_order["status"] = "passed"
            sell_order["result"] = "config mock"
            sell_order["order_data"] = {}
            sell_order["order_data"]["id"] = 123
            sell_order['order_id'] = sell_order["order_data"]["id"]
            sell_order['order_data']["symbol"] = pair
            sell_order['order_data']["price"] = price
            sell_order['order_data']["amount"] = qty
            sell_order['order_data']["filled"] = qty
            sell_order['order_data']["status"] = "closed"
            # buy_order["order_data"] = order
            logger.info("Mocked Market sale order created")
            logger.info(pformat(sell_order))
            metrics.p_order_sell_requests.inc()
        except Exception as e:
            logger.error("exception creating market order")
            logger.error(e, exc_info=True)
            sell_order["status"] = "failed"
            sell_order["result"] = pformat(e)
            sell_order["error_information"] = "exception creating market sale order"
            metrics.p_order_buy_failed.inc()
    logger.debug("Market order result - ")
    logger.debug(pformat(sell_order))
    return sell_order

## Creates a limit buy order, an order for a qty at a specific price
# @retry(wait=wait_random_exponential(multiplier=1, max=60, min=10),reraise=True, stop=stop_after_attempt(60))
def create_limit_buy_order(tracking_number, pair, qty, price):
    markets = exchange.load_markets()
    logger.info(f"create limit buy order - {tracking_number} - {pair} - {qty} - {price}")
    buy_order = {}
    buy_order["qty"] = exchange.amount_to_precision(pair, qty)
    buy_order["pair"] = pair
    buy_order["price"] = exchange.price_to_precision(pair, price)
    buy_order["order_type"] = 'limit'
    buy_order["side"] = 'buy'
    buy_order["params"] = {}
    buy_order["current_market"] = fetch_ticker(pair)
    buy_order["status"] = "init"
    buy_order["result"] = {}
    if config["binance"]["mock"] == False:
        try:
            order = exchange.create_order(buy_order["pair"], buy_order["order_type"], buy_order["side"], buy_order["qty"],
            buy_order["price"], buy_order["params"])
            buy_order["status"] = "passed"
            buy_order["result"] = order
            logger.info("Limit buy order created")
            logger.info(pformat(buy_order))
        except Exception as e:
            logger.error("Issue inserting into DB")
            logger.error(e, exc_info=True)
            buy_order["status"] = "failed"
            buy_order["result"] = pformat(e)
    else:
        logger.info("MOCK ACTIVE - NOT CREATING BUY ORDER")
        logger.info(pformat(buy_order))
        buy_order["status"] = "mock"
        buy_order["result"] = {}
    logger.trace("limit order result - ")
    logger.trace(pformat(buy_order))
    return buy_order

def fetch_binance_order(orderid, pair, table_order_id):
    if not config['binance']['mock']:
        if orderid and pair:
            logger.debug(f"Checking Buy Order - {pair} - {str(orderid)}")
            try:
                order = exchange.fetchOrder(orderid, pair)
                logger.debug("Order Status")
                logger.debug(f"Status - {order['status']}")
                logger.debug(f"Price - {order['price']:.8f}")
                logger.debug(f"Ordered - {order['amount']:.8f}")
                logger.debug(f"Remaining - {order['remaining']:.8f}")
                logger.debug(f"Filled - {order['filled']:.8f}")
                order["success"] = True
            except:
                logger.error(traceback.print_exc())
                order = {}
                order["success"] = False
        else:
            order = {}
    else:
        logger.debug("MOCK IS ACTIVE!!")
        logger.debug("MOCK IS ACTIVE!!")
        logger.debug("MOCK IS ACTIVE!!")
        order_tab = logic.fetch_order(table_order_id)
        order = {}
        order["success"] = True
        order['status'] = "FILLED"
        order['price'] = order_tab.executed_price
        order['amount'] = order_tab.executed_qty
        order['remaining'] = 0
        order['filled'] = order_tab.executed_qty
    logger.trace(pformat(order))
    return order