#!/bin/python3

import os, sys, traceback, json, time
sys.path.append(r'./modules')

from envyaml import EnvYAML
from pprint import pformat
from datetime import datetime, timezone
from random import randint

from modules.logger import setup_custom_logger

from concurrent.futures.thread import ThreadPoolExecutor
from modules.camunda.external_task.external_task_worker import ExternalTaskWorker

from modules.camunda.external_task.external_task import ExternalTask
from modules.camunda.process_definition.process_definition_client import ProcessDefinitionClient

import modules.bpm as bpm, modules.shared_libs as shared_libs
import logic, metrics, models

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

def setup_bpm_subscriptions():
    logger.debug("Set up subscriptions")
    topics = [
        ("ValidateBinanceOrderRequest", handle_ValidateBinanceOrderRequest),
        ("BinanceValidateAssetBalance", handle_BinanceValidateAssetBalance),
        ("BinanceOrdersAllowed", handle_BinanceOrdersAllowed),
        ("CreateSpotMarketBuyOrder", handle_CreateSpotMarketBuyOrder),
        ("ValidateSpotMarketBuyOrder", handle_ValidateSpotMarketBuyOrder),
        ("CompleteSpotMarketBuyOrder", handle_CompleteSpotMarketBuyOrder),
        ("CreateSpotMarketSellOrder", handle_CreateSpotMarketSellOrder),
        ("ValidateSpotMarketSellOrder", handle_ValidateSpotMarketSellOrder),
        ("CompleteSpotMarketSellOrder", handle_CompleteSpotMarketSellOrder),
    ]
    if topics:
        executor = ThreadPoolExecutor(max_workers=len(topics))
        for index, topic_handler in enumerate(topics):
            topic = topic_handler[0]
            handler_func = topic_handler[1]
            executor.submit(ExternalTaskWorker(worker_id=index, config=bpm.default_bpm_config).subscribe, topic, handler_func)
            logger.debug(f"subscribed - {topic}")
        time.sleep(0.17)
    else:
        logger.info("No topics to subscribe to")

def handle_ValidateBinanceOrderRequest(task: ExternalTask):
    logger.trace(f"handle_ValidateBinanceOrderRequest - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        result = logic.store_new_market_order(vars['tracking_number'], vars['market'], vars['order_type'], vars['qty'], vars['price'], vars['origin_process_id'])
        if result['success']:
            order = logic.fetch_order(result['id'])
            if order.id:
                if float(vars['qty']) > 0.0 and float(vars['price']) > 0.0:
                    logger.info(f"Executable order received")
                    return task.complete({"order_table_id": order.id})
                else:
                    logger.error("Order has zero qty or zero price")
                    return task.bpmn_error("501", "Error handle_ValidateBinanceOrderRequest", {"error": "Order has zero qty or zero price"})
            else:
                logger.error(f"Order not found in DB")
                return task.bpmn_error("501", "Order not found in DB", vars)
        else:
            logger.error(f"Order store to db error")
            return task.bpmn_error("501", "Order store error", vars)
    except Exception:
        logger.error(f"Exception handle_ValidateBinanceOrderRequest")
        logger.error(traceback.format_exc())
        return task.bpmn_error("501", "Exception handle_ValidateBinanceOrderRequest", {"exception": traceback.format_exc()})

def handle_BinanceValidateAssetBalance(task: ExternalTask):
    logger.trace(f"handle_BinanceValidateAssetBalance - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            logger.info("This is not implemented yet, the idea being that an existing balance might be sufficient, but not sure what to do yet")
            logger.info("funding was already validated during funding decisioning")
            return task.complete({"order_table_id": order.id})
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("501", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_BinanceValidateAssetBalance")
        logger.error(traceback.format_exc())
        return task.bpmn_error("501", "Exception handle_BinanceValidateAssetBalance", {"exception": traceback.format_exc()})

def handle_BinanceOrdersAllowed(task: ExternalTask):
    logger.trace(f"handle_BinanceOrdersAllowed - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id and config['binance']['orders_allowed']:
            return task.complete({"order_table_id": order.id})
        else:
            logger.error(f"Order not found in DB, or orders disabled in config")
            return task.bpmn_error("502", "Order not found in DB, or orders disabled in config", vars)
    except Exception:
        logger.error(f"Exception handle_BinanceOrdersAllowed")
        logger.error(traceback.format_exc())
        return task.bpmn_error("502", "Exception handle_BinanceOrdersAllowed", {"exception": traceback.format_exc()})

def handle_CreateSpotMarketBuyOrder(task: ExternalTask):
    logger.trace(f"handle_CreateSpotMarketBuyOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            result = logic.create_spot_market_buy_order(vars['order_table_id'], order.tracking_number, order.market, order.qty, order.price, order.order_type)
            logger.debug(pformat(result))
            logger.debug(f"QTY - {order.qty}")
            if result["success"]:
                logger.info("Binance market order created, commiting info to table")
                db_result = logic.update_order_status(vars['order_table_id'], order.tracking_number, order.order_type, "PLACED", "", result['order_data'], result["order_id"])
                if db_result['success']:
                    return task.complete({"order_table_id": order.id})
            else:
                logger.error("Binance market entry order validation failed")
                db_result = logic.update_order_status(vars['order_table_id'], order.tracking_number, order.order_type, "PLACEMENT_ERROR", "", result['order_data'], "check_order_data")
                return task.bpmn_error("503", "Order creation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("503", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_CreateSpotMarketBuyOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("503", "Exception handle_CreateSpotMarketBuyOrder", {"exception": traceback.format_exc()})

def handle_ValidateSpotMarketBuyOrder(task: ExternalTask):
    logger.trace(f"handle_ValidateSpotMarketBuyOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.info("THIS IS INCOMPLETE!")

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            result = logic.validate_spot_market_buy_order(order.order_id, vars["market"], vars['order_table_id'])
            logger.debug(pformat(result))
            if result["success"]:
                logger.info("Binance market order validated, commiting info to table")
                db_result = logic.update_order_status(vars['order_table_id'],order.tracking_number, order.order_type, "FILLED", "", result['order_data'], order.order_id)
                if db_result['success']:
                    return task.complete({"order_table_id": order.id, "buy_order_validation": json.dumps(result)})
            else:
                logger.error("Binance market entry order validation failed")
                db_result = logic.update_order_status(vars['order_table_id'],order.tracking_number, order.order_type, "VALIDATION_ERROR", "", result['order_data'], order.order_id)
                return task.bpmn_error("504", "Order validation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("504", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_ValidateSpotMarketBuyOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("504", "Exception handle_ValidateSpotMarketBuyOrder", {"exception": traceback.format_exc()})

def handle_CompleteSpotMarketBuyOrder(task: ExternalTask):
    logger.trace(f"handle_CompleteSpotMarketBuyOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            if vars["buy_order_validation"]:
                logger.debug("buy order validation block exists, checking")
                logger.debug(f"{vars['buy_order_validation']}")
                logger.error("Add stuff here to improve")
                logger.debug("Checking what state the process is at")
                process_status = bpm.fetch_activities_by_process_id(vars['origin_process_id'])
                logger.debug(f"{process_status}")
                active_task = bpm.resolve_current_process_task(process_status)
                logger.debug(f"{active_task}")
                time.sleep(1)
                bpm.bpm_send_message(vars['origin_process_id'], vars["tracking_number"], "SignalEntryOrderCompleted", {"entry_order_success": True, "qty_purchased": f"{order.executed_qty:.8f}", "price_purchased": f"{order.executed_price:.8f}"}) 
                return task.complete({"order_table_id": order.id})
            else:
                logger.error("Order completion not performed, missing validation")
                return task.bpmn_error("505", "Order validation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("505", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_CompleteSpotMarketBuyOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("505", "Exception handle_CompleteSpotMarketBuyOrder", {"exception": traceback.format_exc()})

def handle_CreateSpotMarketSellOrder(task: ExternalTask):
    logger.trace(f"handle_CreateSpotMarketSellOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            result = logic.create_spot_market_sell_order(vars['order_table_id'], order.tracking_number, order.market, order.qty, order.price, order.order_type)
            logger.debug(pformat(result))
            logger.debug(f"QTY - {order.qty}")
            if result["success"]:
                logger.info("Binance market order created, commiting info to table")
                db_result = logic.update_order_status(vars['order_table_id'], order.tracking_number, order.order_type, "PLACED", "", result['order_data'], result["order_id"])
                if db_result['success']:
                    return task.complete({"order_table_id": order.id})
                else:
                    logger.error("Error updating db")
                    return task.bpmn_error("503", "Order commit failed", {"db_result": db_result})
            else:
                logger.error("Binance market sell order validation failed")
                logger.error(result)
                db_result = logic.update_order_status(vars['order_table_id'], order.tracking_number, order.order_type, "PLACEMENT_ERROR", "viability failed", {}, result["order_id"])
                return task.bpmn_error("503", "Order creation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("503", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_CreateSpotMarketSellOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("503", "Exception handle_CreateSpotMarketSellOrder", {"exception": traceback.format_exc()})

def handle_ValidateSpotMarketSellOrder(task: ExternalTask):
    logger.trace(f"handle_ValidateSpotMarketSellOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.error("THIS IS INCOMPLETE!")

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            result = logic.validate_spot_market_sell_order(order.order_id, vars["market"], vars['order_table_id'])
            logger.debug(pformat(result))
            if result["success"]:
                logger.info("Binance market order validated, commiting info to table")
                db_result = logic.update_order_status(vars['order_table_id'],order.tracking_number, order.order_type, "FILLED", "", result['order_data'], order.order_id)
                if db_result['success']:
                    return task.complete({"order_table_id": order.id, "buy_order_validation": json.dumps(result)})
            else:
                logger.error("Binance market sell order validation failed")
                db_result = logic.update_order_status(vars['order_table_id'],order.tracking_number, order.order_type, "VALIDATION_ERROR", "", result['order_data'], order.order_id)
                return task.bpmn_error("504", "Order validation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("504", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_ValidateSpotMarketSellOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("504", "Exception handle_ValidateSpotMarketSellOrder", {"exception": traceback.format_exc()})

def handle_CompleteSpotMarketSellOrder(task: ExternalTask):
    logger.trace(f"handle_CompleteSpotMarketSellOrder - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        order = logic.fetch_order(vars['order_table_id'])
        if order.id:
            if vars["buy_order_validation"]:
                logger.debug("sell order validation block exists, checking")
                logger.debug(f"{vars['buy_order_validation']}")
                logger.error("Add stuff here to improve")
                logger.debug("Checking what state the process is at")
                process_status = bpm.fetch_activities_by_process_id(vars['origin_process_id'])
                logger.debug(f"{process_status}")
                active_task = bpm.resolve_current_process_task(process_status)
                logger.debug(f"{active_task}")
                time.sleep(5) # Don't remove this, the camunda must step a bit 
                if active_task["success"]:
                    logger.debug("Active task retrieved, checking process state")
                    if active_task["activity_id"] == "BinanceUpdateOrderResponseGateway":
                        bpm.bpm_send_message(vars['origin_process_id'], vars["tracking_number"], "BinanceUpdateOrderSuccess", {"binance_order_data": order.order_data, "sell_order_success": True, "qty_sold": f"{order.executed_qty:.8f}", "price_sold": f"{order.executed_price:.8f}"})
                    else:
                        logger.error("Process not found to be in the correct state")
                        return task.bpmn_error("505", "Cannot inform parent process of order status", {})
                return task.complete({"order_table_id": order.id})
            else:
                logger.error("Order completion not performed, missing validation")
                bpm.bpm_send_message(vars['origin_process_id'], vars["tracking_number"], "BinanceUpdateOrderFailure", {"binance_order_data": order.order_data, "sell_order_success": False, "qty_sold": f"{0.0:.8f}"})
                return task.bpmn_error("505", "Order validation failed", vars)
        else:
            logger.error(f"Order not found in DB")
            return task.bpmn_error("505", "Order not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_CompleteSpotMarketSellOrder")
        logger.error(traceback.format_exc())
        return task.bpmn_error("505", "Exception handle_CompleteSpotMarketSellOrder", {"exception": traceback.format_exc()})