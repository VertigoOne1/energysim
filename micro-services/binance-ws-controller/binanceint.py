#!/bin/python3

## Binance WebSocket Interface

import os
import sys, json, time, re, math, traceback
import unicorn_binance_websocket_api
from unicorn_fy.unicorn_fy import UnicornFy
import threading
from random import randint
from datetime import datetime, timedelta
from pprint import pformat
import envyaml, apicontroller
from modules.logger import setup_custom_logger
import logic, metrics
from envyaml import EnvYAML

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

binance_websocket_api_manager = unicorn_binance_websocket_api.BinanceWebSocketApiManager(exchange="binance.com", output_default="UnicornFy")

active_feeds = []

def process_stream_data(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            try:
                logger.trace("Stream Data Packet - ")
                logger.trace(pformat(oldest_stream_data_from_stream_buffer))
                if "id" in oldest_stream_data_from_stream_buffer:
                    logger.trace("Not market data event")
                elif "event_time" in oldest_stream_data_from_stream_buffer:
                    logger.trace("Trade data event, transmitting")
                    ## This is going to get busy, so lets split out the topics name to the tracking_number at some point
                    logic.emit_trade_data_event(oldest_stream_data_from_stream_buffer)
                    metrics.p_market_data_events.inc()
            except Exception:
                logger.error(traceback.format_exc())
                logger.error("Issue with response from binance controller")
                # not able to process the data? write it back to the stream_buffer
                # binance_websocket_api_manager.add_to_stream_buffer(oldest_stream_data_from_stream_buffer)

def start_ws_stream(pair, tracking_number, type):
    if not check_existing_feeds(tracking_number, type):
        logger.trace("feed not found, creating new stream")
        pair = pair.lower()
        markets = [pair]
        try:
            feed = binance_websocket_api_manager.create_stream(type, markets, api_key=config['binance']['live_apikey'], api_secret=config['binance']['live_secret'], stream_label=tracking_number)
            active_feeds.append(feed)
            metrics.p_active_feeds.set(len(active_feeds))
            binance_websocket_api_manager.print_summary()
            # logger.debug(pformat(binance_websocket_api_manager.print_stream_info(feed)))
            feedinfo = {}
            feedinfo["status"] = "active"
            feedinfo["success"] = True
            feedinfo["tracking_number"] = tracking_number
            feedinfo["pair"] = pair
            feedinfo["type"] = type
            feedinfo["detail"] = binance_websocket_api_manager.get_stream_info(feed)
            feedinfo["error_information"] = ""
            logger.trace(pformat(feedinfo))
            metrics.p_ws_feeds_started.inc()
            return feedinfo
        except Exception:
            logger.error(traceback.format_exc())
            logger.error("Issue with response from binance ws controller")
            feedinfo = {}
            feedinfo["status"] = "failed"
            feedinfo["success"] = False
            feedinfo["pair"] = pair
            feedinfo["tracking_number"] = tracking_number
            feedinfo["type"] = type
            feedinfo["error_information"] = traceback.format_exc()
        return feedinfo
    else:
        logger.debug("feed already active")
        binance_websocket_api_manager.print_summary()
        feedinfo = {}
        feedinfo["status"] = "active"
        feedinfo["success"] = True
        feedinfo["tracking_number"] = tracking_number
        feedinfo["type"] = type
        feedinfo["detail"] = get_existing_feed(tracking_number)
        feedinfo["error_information"] = ""
        logger.trace(pformat(feedinfo))
        return feedinfo

def get_existing_feed(tracking_number):
    logger.debug(f"get_existing_feed - {tracking_number}")
    default = {}
    for feed in active_feeds:
        logger.trace(f"Checking feed - {feed}")
        feedinfo = binance_websocket_api_manager.get_stream_info(feed)
        logger.trace(feedinfo)
        if (feedinfo["stream_label"] == tracking_number):
            logger.trace(f"Existing feed matched to - {tracking_number}")
            return feedinfo
        else:
            logger.warn(f"No feed matched tracking number - {tracking_number}")
            return {}
    return default

def check_existing_feeds(tracking_number, type):
    logger.debug(f"check_existing_feeds - {tracking_number} - {type}")
    logger.debug(f"Active feeds - {active_feeds}")
    matched = False
    if len(active_feeds) > 0:
        for feed in active_feeds:
            logger.trace(f"Checking feed - {feed}")
            feedinfo = binance_websocket_api_manager.get_stream_info(feed)
            if (feedinfo["stream_label"] == tracking_number) and (type in feedinfo["channels"]):
                logger.trace(f"Already have this type of feed for - {tracking_number}")
                matched = True
    else:
        logger.debug("No existing feeds")
    return matched

## MARNUS - NEED TO NOT REMOVE FEEDS WHEN THERE ARE MULTIPLE
def stop_ws_stream(pair, tracking_number, type):
    removed = False
    feedinfo = {}
    feedinfo["status"] = "stop"
    feedinfo["tracking_number"] = tracking_number
    feedinfo["type"] = type
    feedinfo["detail"] = {}
    feedinfo["error_information"] = ""
    if active_feeds and len(active_feeds) > 0:
        for feed in active_feeds:
            info = binance_websocket_api_manager.get_stream_info(feed)
            feedinfo["detail"] = info
            if info["markets"] and len(info["markets"]) > 0:
                for market in info["markets"]:
                    if market == pair.lower():
                        logger.info(f"Stopping feed - {market}")
                        binance_websocket_api_manager.stop_stream(feed)
                        active_feeds.remove(feed)
                        metrics.p_active_feeds.set(len(active_feeds))
                        removed = True
                        metrics.p_ws_feeds_stopped.inc()
                        feedinfo["success"] = True
                        return feedinfo
    else:
        feedinfo["status"] = "notfound"
        feedinfo["success"] = True
        feedinfo["tracking_number"] = tracking_number
        feedinfo["type"] = type
        feedinfo["detail"] = {}
        feedinfo["error_information"] = ""
        logger.trace(feedinfo)
        return feedinfo
    if removed:
        feedinfo["status"] = "stopped"
        feedinfo["success"] = True
        feedinfo["tracking_number"] = tracking_number
        feedinfo["type"] = type
        feedinfo["error_information"] = ""
        logger.trace(feedinfo)
        return feedinfo
    binance_websocket_api_manager.print_summary()

# def updatekline_1m(kline):
#     logger.debug("updatekline_1m")
#     for signal in signals["sigs"]:
#         logger.debug(signal)
#         logger.debug(pformat(kline))
#         if signal["pair"] == kline["data"]["s"]:
#             logger.debug("Matched signal to a kline - " + str(kline["data"]["s"]))
#             logger.debug("Current timestamp - " + str(kline["data"]["k"]["t"]))
#             # Removing old klines for the same minute
#             if len(signal["kline_history_1m"]) > 0:
#                 for i in range(len(signal["kline_history_1m"])):
#                     logger.debug("Checking kline - " + str(signal["kline_history_1m"][i]["t"]))
#                     if signal["kline_history_1m"][i]["t"] == kline["data"]["k"]["t"]:
#                         logger.debug("Remove existing kline")
#                         signal["kline_history_1m"].pop(i)
#                     else:
#                         logger.debug("Unique kline, skipping")
#             # Add the latest kline
#             signal["kline_history_1m"].append(kline["data"]["k"])
#             # Keeping the last x minutes
#             if len(signal["kline_history_1m"]) > MAX_1M_KLINE_HISTORY:
#                 logger.debug("Pruning kline history")
#                 signal["kline_history_1m"].pop(0)
#             if len(signal["kline_history_1m"]) >= RSI_PERIOD:
#                 signal["last_rsi"] = calcRSI(signal)
#             update_signal_status_kline(signal)
#             calculate_status(signal)
#             logger.debug(pformat(signal))
#             close_prices_long = []
#             close_prices_short = []
#             i = 0
#             for kl in signal["kline_history_1m"]:
#                 i = i + 1
#                 readable = datetime.fromtimestamp(kl["t"]/1000).isoformat()
#                 logger.debug(readable + " - " + str(kline["data"]["s"]) + " - Close: " + str(kl["c"]))
#                 close_prices_long.append(kl["c"])
#                 close_prices_short.append(kl["c"])
#             if i >= M_AVG_SHORT:
#                 close_prices_short = close_prices_long[-M_AVG_SHORT:]
#             signal["close_trend_long"] = get_trend(close_prices_long)
#             signal["close_trend_short"] = get_trend(close_prices_short)
#             logger.debug("Close Trend 10 - " + str(pformat(close_prices_long)))
#             logger.debug("Close Trend 5 - " + str(pformat(close_prices_short)))

# def updateBookData(book):
#     logger.debug("updateBookData")
#     for signal in signals["sigs"]:
#         logger.debug(signal)
#         logger.debug(pformat(book))
#         if signal["pair"] == book["data"]["s"]:
#             logger.debug("Matched signal to a book message - " + str(book["data"]["s"]))
#             signal["best_bid"] = book["data"]["b"]
#             signal["best_ask"] = book["data"]["a"]
#             signal["last_price"] = book["data"]["a"]
#             # calculate_status(signal)

# def updateTickerData(ticker):
#     logger.debug("updateTickerData")
#     for signal in signals["sigs"]:
#         logger.debug(signal)
#         logger.debug(pformat(ticker))
#         if signal["pair"] == ticker["s"]:
#             logger.debug("Matched signal to a ticker message - " + str(ticker["s"]))
#             # signal["close_price"] = ticker["c"]
#             # signal["low_price"] = ticker["l"]
#             # signal["high_price"] = ticker["h"]
#             # signal["last_timestamp"] = ticker["E"]
#             # signal["open_price"] = ticker["o"]
#             signal["volume"] = ticker["v"]
#             signal["qty"] = ticker["q"]
#             signal["last_price"] = ticker["c"]

def restart_state(active_feeds):
    logger.debug("Re-initialising feeds from last known positions")
    if active_feeds["success"] and len(active_feeds['feeds']) > 0:
        for feed in active_feeds['feeds']:
            if feed.status == "active" or feed.status == "started":
                logger.debug(f"Reinitialising - {feed.pair}")
                if not check_existing_feeds(feed.tracking_number, type):
                    start_ws_stream(feed.pair, feed.tracking_number, feed.type)
                    time.sleep(15) # Don't remove
    else:
        logger.debug("No feeds to re-initialise")
    logger.info("Completed re-initialisation routine")

logger.info("Starting worker thread")
worker_thread = threading.Thread(target=process_stream_data, args=(binance_websocket_api_manager,))
worker_thread.start()