#!/bin/python3

from multiprocessing.connection import wait
import sys, traceback, os
sys.path.append(r'./modules')

from envyaml import EnvYAML
from pprint import pformat
from datetime import datetime, timezone
from random import randint
import json, time

from modules.logger import setup_custom_logger

from concurrent.futures.thread import ThreadPoolExecutor
from modules.camunda.external_task.external_task_worker import ExternalTaskWorker

from modules.camunda.external_task.external_task import ExternalTask
from modules.camunda.process_definition.process_definition_client import ProcessDefinitionClient

import modules.bpm as bpm, modules.shared_libs as shared_libs
import logic, metrics

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
        ("EntryPointProcessing", handle_EntryPointProcessing),
        ("RequestTradeDataFeed", handle_RequestTradeDataFeed),
        ("ValidateMarketFeed", handle_ValidateMarketFeed),
        ("ProcessEntryResult", handle_ProcessEntryResult)
    ]
    executor = ThreadPoolExecutor(max_workers=len(topics))
    for index, topic_handler in enumerate(topics):
        topic = topic_handler[0]
        handler_func = topic_handler[1]
        executor.submit(ExternalTaskWorker(worker_id=index, config=bpm.default_bpm_config).subscribe, topic, handler_func)
        logger.debug(f"subscribed - {topic}")
        time.sleep(0.17)

def handle_EntryPointProcessing(task: ExternalTask):
    logger.trace(f"handle_EntryPointProcessing - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    logger.debug(f"Market - {vars['pair']} - Entry High - {vars['entry_high']}")
    logger.debug(f"Market - {vars['pair']} - Entry Low - {vars['entry_low']}")
    logger.debug(f"Market - {vars['pair']} - Stoploss   - {vars['stoploss']}")

    try:
        new_entry = logic.new_entry_record(vars,str(task.get_process_instance_id()))
        if new_entry['success']:
            logger.debug(f"Entry Added to DB")
            logger.debug(f"{new_entry}")
            return task.complete({"entry_id": new_entry["id"]})
        else:
            logger.error(f"Issue adding entry to DB")
            return task.failure("Error", "Issue adding entry to DB", 0, 0)
            # return task.bpmn_error("501", "Signal not in DB", vars)
    except Exception:
        logger.error(f"Exception handle_EntryPointProcessing")
        logger.error(traceback.format_exc())
        return task.bpmn_error("502", "Exception handle_EntryPointProcessing", {"exception": traceback.format_exc()})

def handle_RequestTradeDataFeed(task: ExternalTask):
    logger.trace(f"handle_RequestTradeDataFeed - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    logger.debug(f"Feed Request - {vars['tracking_number']} - {vars['pair']}")
    logger.debug(f"{task.get_process_instance_id()}")

    time.sleep(2)

    try:
        result = logic.request_start_trade_data(vars['tracking_number'], vars['pair'], "trade")
        db_result = logic.update_entry_process_id(vars['entry_id'], str(task.get_process_instance_id()))
        if result['success'] and db_result['success']:
            logger.debug(f"Trade data request submitted")
            logger.debug(f"{result}")
            db_result = logic.update_entry_status(vars['entry_id'],"active","TRADE_DATA_REQUESTED","",f"{result}")
            return task.complete({"trade_data_request_result": f"{result}", "trade_data_request_db_result": f"{db_result}" })
        else:
            logger.error(f"Issue requesting trade data or updating the db")
            return task.bpmn_error("507", "trade_data_request_issue", f"{result}")
    except Exception:
        logger.error(f"Exception handle_RequestTradeDataFeed")
        logger.error(traceback.format_exc())
        return task.bpmn_error("507", "Exception handle_RequestTradeDataFeed", {"exception": traceback.format_exc()})

def handle_ValidateMarketFeed(task: ExternalTask):
    logger.trace(f"handle_ValidateMarketFeed - {task.get_summary()}")
    FEED_LOOP_WAIT_TIME = 10
    FEED_LOOP_CYCLE_COUNT = 12
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    time.sleep(2)
    session = logic.db_session()
    try:
        session.commit()
        entry = logic.fetch_entry_record(vars["entry_id"])['result']
        if entry.feed_validated:
            logger.info(f"Entry - {vars['tracking_number']} is receiving data")
            db_result = logic.update_entry_status(vars['entry_id'],"active","STARTED","","")
            return task.complete({})
        else:
            waiting = False
            loops = 0
            while waiting == False:
                logger.debug(f"Waiting for feed validation - {vars['tracking_number']}")
                time.sleep(FEED_LOOP_WAIT_TIME)
                session.commit()
                entry = logic.fetch_entry_record(vars["entry_id"])['result']
                if entry.feed_validated:
                    logger.info(f"Entry - {vars['tracking_number']} is receiving data")
                    db_result = logic.update_entry_status(vars['entry_id'],"active","MONITORING_ENTRY","","")
                    return task.complete({})
                else:
                    logger.info(f"Entry - {vars['tracking_number']} does not have data coming in yet")
                    loops = loops + 1
                    db_result = logic.update_entry_status(vars['entry_id'],"active","AWAITING_DATA","","")
                if loops == FEED_LOOP_CYCLE_COUNT:
                    logger.error(f"Entry - {vars['tracking_number']} still does not have data after 2 minutes, stopping feed")
                    logic.request_stop_trade_data(vars['tracking_number'], vars['pair'], "trade")
                    db_result = logic.update_entry_status(vars['entry_id'],"in-active","TIMEOUT_WAITING_FOR_DATA","","")
                    return task.bpmn_error("507", f"No data after waiting {FEED_LOOP_CYCLE_COUNT} times {FEED_LOOP_WAIT_TIME} seconds", {"exception": json.dumps(entry)})
    except Exception:
        logger.error(f"Exception handle_ValidateMarketFeed")
        logger.error(traceback.format_exc())
        logic.request_stop_trade_data(vars['tracking_number'], vars['pair'], "trade")
        db_result = logic.update_entry_status(vars['entry_id'],"in-active""EXCEPTION",traceback.format_exc(),"")
        return task.bpmn_error("507", "Exception handle_ValidateMarketFeed", {"exception": traceback.format_exc()})
    finally:
        session.close()

def handle_ProcessEntryResult(task: ExternalTask):
    logger.trace(f"handle_ProcessEntryResult - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        if vars['entry_timer_expired'] and vars['entry_timer_expired'] == "yes":
            logger.warn("Signal has been idle for days, stopping data feed")
            logic.request_stop_trade_data(vars['tracking_number'], vars['pair'], "trade")
            db_result = logic.update_entry_status(vars['entry_id'],"in-active", "NO_ENTRY_IDLE_TIMEOUT","","")
            return task.bpmn_error("532", "Signal Entry Expiry", {})
        elif vars['entry_point_reached'] and vars['entry_point_reached'] == "yes":
            logger.info(f"Entry Point reached - {vars['entry_price']}")
            logic.request_stop_trade_data(vars['tracking_number'], vars['pair'], "trade")
            db_result = logic.update_entry_status(vars['entry_id'],"in-active","ENTRY_REACHED","","")
            return task.complete({})
        elif vars['update_message_received'] and vars['update_message_received'] == "yes":
            logger.info("Update message received before entry point was done")
            logic.request_stop_trade_data(vars['tracking_number'], vars['pair'], "trade")
            db_result = logic.update_entry_status(vars['entry_id'],"in-active","UPDATE_MSG_BEFORE_ENTRY","","")
            return task.bpmn_error("532`", "Signal entry missed, update message received for signal", {})
        else:
            logger.error("How did you get here")
            return task.failure("Error", "Unreachable point in handle_ProcessEntryResult", 0, 0)
    except Exception:
        logger.error(f"Exception handle_ProcessEntryResult")
        logger.error(traceback.format_exc())
        return task.bpmn_error("532", "Exception handle_ProcessEntryResult", {"exception": traceback.format_exc()})
