#!/bin/python3

import sys, traceback, json, time, os
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
        ("SignalAcceptance", handle_SignalAcceptance),
        ("ValidateMarket", handle_ValidateMarket),
        ("ValidateDenominators", handle_ValidateDenominators),
        ("ValidateEntryPoint", handle_ValidateEntryPoint),
        ("ValidationAcceptance", handle_ValidationAcceptance),
        ("SignalFunding", handle_SignalFunding),
        ("DetermineFunding", handle_DetermineFunding),
        ("AcceptFunding", handle_AcceptFunding),
        ("AcceptFundingProcess", handle_AcceptFundingProcess),
        ("EntryExecution", handle_EntryExecution),
        ("EntryAssessment", handle_EntryAssessment),
        ("CalculateTargetFunding", handle_CalculateTargetFunding),
        ("AcceptEntryProcess",handle_AcceptEntryProcess),
        ("EnableTargetMatching", handle_EnableTargetMatching),
        ("ProcessUpdateInstruction", handle_ProcessUpdateInstruction),
        ("ProcessUpdateExecution", handle_ProcessUpdateExecution),
        ("ContinueOrEndSignal", handle_ContinueOrEndSignal),
        ("AssessSignalPerformance", handle_AssessSignalPerformance),
        ("FinaliseFailedSignalPositions", handle_FinaliseFailedSignalPositions),
        ("CloseOutSignal", handle_CloseOutSignal),
        ("ArchiveSignal", handle_ArchiveSignal)
        # ("EntryPointProcessing", handle_EntryPointProcessing),
        # ("EmitResetSignalEvent", handle_EmitResetSignalEvent),
    ]
    executor = ThreadPoolExecutor(max_workers=len(topics))
    for index, topic_handler in enumerate(topics):
        topic = topic_handler[0]
        handler_func = topic_handler[1]
        executor.submit(ExternalTaskWorker(worker_id=index, config=bpm.default_bpm_config).subscribe, topic, handler_func)
        logger.debug(f"subscribed - {topic}")
        time.sleep(0.17)

def handle_SignalAcceptance(task: ExternalTask):
    logger.info(f"handle_SignalAcceptance - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    result = logic.decode_new_signal_event(vars['new_signal_event'])
    if result['success']:
        logger.info(f"{result}")
        sig_id = result['id']

    try:
        sig = logic.fetch_signal(sig_id)
        if sig:
            logger.debug(f"Signal in DB")
            logger.debug(f"{sig}")
            if config["general"]["signal_processing_allowed"]:
                logic.update_signal_process_id(sig_id, sig["tracking_number"],str(task.get_process_instance_id()))
                return task.complete({"tracking_number": sig["tracking_number"], "signal_id": sig_id})
        else:
            logger.error(f"Signal not in DB")
            return task.bpmn_error("586", "Signal not in DB", vars)
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("586", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_ValidationAcceptance(task: ExternalTask):
    logger.trace(f"handle_SignalAcceptance - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.debug(f"Validation Acceptance")
            logger.trace(f"{sig}")
            if config["general"]["signal_processing_allowed"]:
                return task.complete({"tracking_number": sig["tracking_number"], "validation_success": True })
        else:
            logger.error(f"Signal not in DB")

            return task.bpmn_error("501", "Signal not in DB", vars)
    except Exception:
        logger.error(f"Exception accepting validation")
        logger.error(traceback.format_exc())
        return task.bpmn_error("503", "Exception accepting validation", {"exception": traceback.format_exc()})

def handle_ValidateMarket(task: ExternalTask):
    logger.trace(f"handle_ValidateMarket - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            result = logic.validate_market(sig['pair'])
            if result['success']:
                logger.debug("Signal market validated")
                logger.debug(f"{result}")
                market_result = logic.fetch_market(sig['pair'])
                if market_result['success']:
                    logger.debug("Received market information")
                    logger.debug(market_result)
                    return task.complete({"ticker": json.dumps(result), "market_info": json.dumps(market_result)})
                else:
                    logger.error("Didn't receive minimum market/pair information - market failed")
                    return task.bpmn_error("502", "Signal market validation failure - market failed", result)
            else:
                return task.bpmn_error("502", "Signal market validation failure - ticker failed", result)
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("500", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception market validation")
        logger.error(traceback.format_exc())
        return task.bpmn_error("500", "Exception market validation", {"exception": traceback.format_exc()})

def handle_SignalFunding(task: ExternalTask):
    import time
    logger.trace(f"handle_SignalFunding - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.debug("Entering signal funding sub")

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            result = {}
            result['success'] = True
            if result['success']:
                logger.debug("Signal Funding Main")
                logger.debug(f"{result}")
                return task.complete({"signal_funding_main": json.dumps(result)})
            else:
                return task.bpmn_error("502", "Signal funding bonked", result)
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("502", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception signal funding")
        logger.error(traceback.format_exc())
        return task.bpmn_error("504", "Exception signal funding", {"exception": traceback.format_exc()})

def handle_DetermineFunding(task: ExternalTask):
    import time
    logger.trace(f"handle_DetermineFunding - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            result = logic.check_signal_funding(json.loads(vars['ticker'])['ticker']['symbol'])
            if result['success']:
                logger.debug("Funding determined")
                logger.debug(f"{result}")
                logic.update_signal_funding(vars['signal_id'], sig['tracking_number'], result)
                logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"DetermineFunding_complete")
                return task.complete({"signal_funding_main": json.dumps(result)})
            else:
                return task.bpmn_error("502", "Signal funding bonked", result)
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("502", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_DetermineFunding")
        logger.error(traceback.format_exc())
        return task.bpmn_error("505", "Exception handle_DetermineFunding", {"exception": traceback.format_exc()})

def handle_ValidateEntryPoint(task: ExternalTask):
    logger.trace(f"handle_ValidateEntryPoint - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig and vars['ticker']:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            try:
                market_validation = logic.check_signal_vs_market(json.loads(vars['ticker'])['ticker'], sig)
                if market_validation["success"]:
                    logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"ValidateEntryPoint_complete")
                    return task.complete({"market_validation": json.dumps(market_validation)})
                else:
                    logger.debug("Entry point for the signal failed validation")
                    time.sleep(1)
                    return task.bpmn_error("503", "Entry point for the signal failed validation", {"validation_result": f"{market_validation}", "validation_success": False})
            except Exception:
                logger.debug(traceback.format_exc())
                logger.debug("Exception dealing with entry point checks")
                return task.bpmn_error("503", "Exception dealing with entry point checks", {"exception": traceback.format_exc()})
        else:
            logger.error(f"Signal not found in DB and ticker not in vars")

            return task.bpmn_error("503", "Signal not found in DB and ticker", vars)
    except Exception:
        logger.error(f"Exception handle_ValidateEntryPoint")
        logger.error(traceback.format_exc())
        return task.bpmn_error("508", "Exception handle_ValidateEntryPoint", {"exception": traceback.format_exc()})

def handle_ValidateDenominators(task: ExternalTask):
    logger.trace(f"handle_ValidateDenominators - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig and vars['ticker']:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            logger.debug(f"Ticker Symbol: {json.loads(vars['ticker'])['ticker']['symbol']}")
            try:
                corrected_pricing = logic.check_fix_price_denominator(json.loads(vars['ticker'])['ticker'], sig)
                if corrected_pricing["success"]:
                    logic.update_signal_denomination(sig['id'], sig['tracking_number'], corrected_pricing)
                    logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"ValidateDenominators_complete")
                    return task.complete({"corrected_pricing": json.dumps(corrected_pricing)})
                else:
                    logger.debug("Could not check signal denominators successfully")
                    return task.bpmn_error("503", "Signal denomination validation failure", corrected_pricing)
            except Exception:
                logger.debug(traceback.format_exc())
                logger.debug("Exception dealing with denominator checks")
                return task.bpmn_error("501", "Exception dealing with denominator checks", {"exception": traceback.format_exc(), "signal": sig})
        else:
            logger.error(f"Signal not found in DB and ticker not in vars")
            return task.bpmn_error("501", "Signal not found in DB, and ticker", vars)
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("501", "Exception handle_ValidateDenominators", {"exception": traceback.format_exc()})

def handle_AcceptFunding(task: ExternalTask):
    import time
    logger.trace(f"handle_AcceptFunding - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.debug("Entering signal funding sub")

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            result = {}
            result['success'] = True
            if result['success']:
                logger.debug("Funding Accepted")
                logger.debug(f"{result}")
                logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"AcceptFunding_complete")
                return task.complete({"AcceptFunding": json.dumps(result), "funding_success": True})
            else:
                return task.bpmn_error("502", "Signal funding bonked", {"funding_result": result, "funding_success": False})
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("502", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_AcceptFunding")
        logger.error(traceback.format_exc())
        return task.bpmn_error("505", "Exception handle_AcceptFunding", {"exception": traceback.format_exc()})

def handle_AcceptFundingProcess(task: ExternalTask):
    import time
    logger.trace(f"handle_AcceptFundingProcess - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.debug("Accepting funding process")

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            result = {}
            result['success'] = True
            if result['success']:
                logger.debug("Signal Accepted")
                logger.debug(f"{result}")
                logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"AcceptFunding_complete")
                return task.complete({"AcceptFunding": f"{result}","entry_high": sig['entry_high'], "entry_low": sig['entry_low'], "stoploss": sig['stoploss'], "pair": sig['pair']})
            else:
                return task.bpmn_error("502", "Funded signal not accepted", result)
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("502", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_AcceptFundingProcess")
        logger.error(traceback.format_exc())
        return task.bpmn_error("505", "Exception handle_AcceptFundingProcess", {"exception": traceback.format_exc()})

def handle_EntryExecution(task: ExternalTask):
    logger.trace(f"handle_EntryExecution - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            if vars['entry_point_reached'] and vars['entry_point_reached'] == "yes" and vars['entry_price'] and float(sig['funding_allocated']) > 0.0:
                logger.info(f"Entry point reached - CREATE ORDER - {vars['entry_price']} - {vars['entry_status']}")
                logger.info(f"Funding allocated - {sig['funding_allocated']}")
                if vars['entry_status'] == "spot-buy-market":
                    logger.info(f"Order Type - {vars['entry_status']}")
                    market_info = json.loads(vars['market_info'])
                    if market_info['success']:
                        logger.debug(pformat(market_info['market']))
                        min_lot_size = float(logic.fetch_min_lot_size(market_info))
                        logic.place_market_buy_order(vars['tracking_number'], vars['pair'], vars['entry_price'] ,sig['funding_allocated'],str(task.get_process_instance_id()), min_lot_size)
                        logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"EntryExecution_complete")
                        return task.complete({'qty_min_lot_size': min_lot_size})
                    else:
                        logger.error("Could not fetch market info for necessary calculations of qty")
                        return task.bpmn_error("507", "Error handle_EntryExecution", {"error": "Only spot market buy is implemented"})
                else:
                    return task.bpmn_error("507", "Error handle_EntryExecution", {"error": "Only spot market buy is implemented"})
            else:
                logger.error("Should not be possible, missing variables, and or no funding")
                return task.bpmn_error("507", "Error handle_EntryExecution", {"error": "Insuffient variable data to create order, entry_price, funding_allocated"})
        else:
            logger.error(f"Signal not found in DB")
            return task.bpmn_error("507", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_EntryExecution")
        logger.error(traceback.format_exc())
        return task.bpmn_error("507", "Exception handle_EntryExecution", {"exception": traceback.format_exc()})

def handle_EntryAssessment(task: ExternalTask):

    ### TO CHECK IF EVERYTHING IS FINE, WE SHOULD HAVE AN ENTRY AT A PRICE CLOSE TO THE MARKET VALUES AND THE SIGNAL

    logger.trace(f"handle_EntryAssessment - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            if vars['entry_complete_message'] == "yes":
                if float(vars['qty_purchased']) > 0.0:
                    logger.debug(f"Qty Purchased: {vars['qty_purchased']}")
                    logic.update_signal_executed_qty(vars['signal_id'], vars['tracking_number'], float(vars['qty_purchased']), float(vars['price_purchased']))
                    logic.update_signal_qty_remaining(vars['signal_id'], float(vars['qty_purchased']))
                    logger.info("Market entry successfully completed")
                    logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"EntryAssessment_complete")
                    return task.complete({})
                else:
                    logger.error("Market entry did not result in a usable qty")
                    logger.debug(f"Qty Purchased: {vars['qty_purchased']}")
                    return task.bpmn_error("506", f"Qty Purchased issue: {vars['qty_purchased']}", {"entry_success": False})
            elif vars['entry_expiry'] == "yes":
                logger.warn("Market entry execution failed")
                return task.bpmn_error("506", "Entry point execution expired, issue with binance?", {"entry_success": False})
            else:
                logger.debug("This should be unreachable, investigate variables")
        else:
            logger.error(f"Signal not in DB")
            return task.bpmn_error("506", "Signal not in DB", vars)
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("506", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_CalculateTargetFunding(task: ExternalTask):

    # how many targets, the target spread, and the distribution of to apply. Remaining qty's for each point.
    # based on qty_purchased

    logger.trace(f"handle_CalculateTargetFunding - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.debug(f"{sig}")
            logger.debug("Targets for distribution - ")
            logger.debug(f"{sig['targets']}")
            if vars['entry_complete_message'] == "yes":
                if float(vars['qty_purchased']) > 0.0:
                    try:
                        result = logic.process_target_funding(vars['signal_id'], float(vars['qty_purchased']), json.loads(vars['market_info']), json.loads(vars['ticker']))
                        if result['success']:
                            logger.debug(f"Qty Purchased: {vars['qty_purchased']}")
                            logger.debug(f"{result['distribution']}")
                            result_db = logic.update_signal_target_distribution(vars['signal_id'], result['distribution'])
                            if result_db['success']:
                                logger.debug("DB Updated with target distribution calc - check db")
                                return task.complete({"target_distribution_success": True})
                            else:
                                logger.error("Issue updating DB")
                                return task.bpmn_error("582", f"Distribution calc storage issue", {"target_distribution_success": False})
                            # logic.update_signal_executed_qty(vars['signal_id'], vars['tracking_number'], float(vars['qty_purchased']), float(vars['price_purchased']))
                            # logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"CalculateTargetFunding_Complete")
                        else:
                            logger.error("Distribution calc error")
                            logger.error(f"{result}")
                            return task.bpmn_error("582", f"Distribution calc issue", {"target_distribution_success": False, "target_distribution_error": json.dumps(result)})
                    except Exception:
                        logger.error(f"Exception calculating target distribution")
                        logger.error(traceback.format_exc())
                else:
                    logger.error("Market entry did not result in a usable qty")
                    logger.debug(f"Qty Purchased: {vars['qty_purchased']}")
                    return task.bpmn_error("582", f"didn't buy a usable qty", {"target_distribution_success": False})
            else:
                logger.debug("This should be unreachable, investigate variables")
                return task.bpmn_error("582", f"didn't trigger on entry completed", {"target_distribution_success": False})
        else:
            logger.error(f"Signal not in DB")
            return task.bpmn_error("582", "Signal not in DB", vars)
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        # return task.bpmn_error("582", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_AcceptEntryProcess(task: ExternalTask):

    logger.trace(f"handle_AcceptEntryProcess - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            if config["general"]["signal_processing_allowed"]:
                if vars['entry_order_success'] and vars['target_distribution_success']:
                    logger.debug(f"Entry successful, target distribution calc good - continuing")
                    logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"AcceptEntryProcess_complete")
                    return task.complete({"entry_success": True})
                else:
                    logger.error(f"Order process failed")
                    return task.complete({"entry_success": False})
            else:
                logger.error(f"Signal processing not allowed further")
                return task.complete({"entry_success": False})
        else:
            logger.error(f"Signal not in DB")
            return task.complete({"entry_success": False})
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("502", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_EnableTargetMatching(task: ExternalTask):
    logger.trace(f"handle_EnableTargetMatching - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    ## Just a holding spot for possible expansion later, this enters into waiting for target messages

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        logger.debug(f"Reported targets: {sig['targets']}")
        target_count = len(sig['targets'])
        logger.debug(f"Number of targets are: {target_count}")
        if sig:
            logger.trace(f"Signal in DB")
            logger.trace(f"{sig}")
            logger.info("Now waiting for signal update messages")
            logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"EnableTargetMatching_complete")
            return task.complete({"num_targets": target_count})
        else:
            logger.error(f"Signal not in DB")
            return task.bpmn_error("512", "Signal not in DB", {})
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("512", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_ProcessUpdateInstruction(task: ExternalTask):
    logger.trace(f"handle_ProcessUpdateInstruction - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    logger.debug(f"Received Update Instruction - {vars['tracking_number']} - {vars['update_type']}")
    update_data = json.loads(vars['update_data'])
    logger.debug("Update data - ")
    logger.debug(f"{update_data}")

    logger.debug("Start Update Processing Process")
    proc_vars = {}
    proc_vars['update_data'] = update_data
    proc_vars['linked_signal_id'] = vars['signal_id']
    proc_vars['signal_process_id'] = str(task.get_process_instance_id())
    proc_vars['pair'] = vars['pair']
    proc_vars['tracking_number'] = update_data['tracking_number']
    proc_vars['target_num'] = vars['target_num']
    proc_vars['num_targets'] = vars['num_targets']
    proc_vars['qty_purchased'] = vars['qty_purchased']
    proc_vars['update_type'] = vars['update_type']
    logger.debug("New update process vars")
    logger.debug(f"{proc_vars}")
    try:
        if vars['target_num'] == "A":
            logger.info("Received end targets state")
            return task.complete({"max_targets_exceeded": False, "close_position": True})
        elif int(vars['target_num']) > int(config['targets']['max_targets_to_process']):
            logger.info("Received a target update that we disabled by config (max targets exceeded process)")
            return task.complete({"max_targets_exceeded": True, "close_position": True, "reset_signal": False})
        else:
            result = bpm.bpm_send_process_start_message(vars['tracking_number'], "StartUpdateMessageProcess", proc_vars)
            if result['success']:
                logger.debug(f"Start process message sent - new process - {result['process_id']}")
                logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"ProcessUpdateInstruction_complete")
                return task.complete({"process_update_process_id": f"{result['process_id']}", "max_targets_exceeded": False, "reset_signal": False, "close_position": False})
            else:
                return task.bpmn_error("592", "Issue starting update process", {"max_targets_exceeded": False, "reset_signal": False})
                # logger.debug("Problem. it will keep looping now")
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("502", "Exception fetching signal", {"exception": traceback.format_exc()})
        # logger.debug("exception. it will keep looping now")

def handle_ProcessUpdateExecution(task: ExternalTask):
    logger.trace(f"handle_ProcessUpdateExecution - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    logger.debug(f"Checking Update Execution - {vars['tracking_number']} - {vars['update_type']}")
    try:
        if "yes" in vars['target_order_executed']:
            logger.debug(f"Looking for - {vars['update_type']}_order_info in variable list")
            if f"{vars['update_type']}_order_info" in vars:
                tvar = f"{vars['update_type']}_order_info"
                logger.debug(f"Found order_info for {vars['update_type']}")
                update_pack = logic.process_order_execution_data(vars[tvar])
                logger.debug(pformat(update_pack))
                # logger.error("Update remaining qty here")
                # time.sleep(60)
                if update_pack['success']:
                    update_id = json.loads(vars[tvar])["update_id"]
                    db_result = logic.update_update_executed_info(update_id, update_pack)
                    if db_result['success']:
                        logger.debug("Order data updated")
                        logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"{vars['update_type']}_order_complete")
                        return task.complete({"target_order_executed": "yes", "update_message_received": "yes"})
                    else:
                        logger.error("Issue updating order data")
                        return task.bpmn_error("512", "Issue checking update process execution", {"target_order_executed": "no"})
                else:
                    logger.error("Update Pack (consolidation) failed")
                    return task.bpmn_error("512", "Issue with order data consolidation", {"target_order_executed": "no"})
            else:
                logger.error(f"Expected update data not found - variable - {vars['update_type']}_order_info")
                return task.bpmn_error("512", "Issue checking update process execution", {"target_order_executed": "no"})
        elif "yes" in vars['target_order_timeout']:
            logger.debug("Order process timed out")
            logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"{vars['update_type']}_timeout")
            return task.complete({"target_order_executed": "no"})
        elif "yes" in vars['target_order_failure']:
            logger.error("Order process failed")
            logic.update_signal_status(vars['signal_id'],vars['tracking_number'],f"{vars['update_type']}_failed")
            return task.complete({"target_order_executed": "no"})
    except Exception:
        logger.error(f"Exception update process execution review")
        logger.error(traceback.format_exc())
        return task.bpmn_error("512", "Exception update process execution review", {"exception": traceback.format_exc()})

def handle_ContinueOrEndSignal(task: ExternalTask):
    logger.trace(f"handle_ContinueOrEndSignal - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    ## Based on the number of targets, stoploss, expiry, we then set a var for continue or end processing
    ## var signal_complete

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig:
            logger.debug(f"Remaining Qty: {sig['qty_remaining']}")
            time.sleep(2)
            if config['targets']['never_end_signal_update_processing']:
                logger.warn("DISABLE IN PRODUCTION")
                logger.warn("Test settings are enabled, signal will never be ended regardless of message received")
                logger.warn("DISABLE IN PRODUCTION")
                logger.warn("resetting to target waiting")
                return task.complete({"signal_complete": False, "target_order_executed": False})
            elif vars['reset_signal']:
                logger.warn("resetting to target waiting by human request after errors")
                return task.complete({"signal_complete": False, "reset_signal": False, "target_order_executed": False})
            elif vars['max_targets_exceeded'] and vars['close_position']:
                return task.complete({})
            end_signal = False
            end_signal_states = ["AllTargetsReachedMessage", "StoplossReachedMessage", "LimitedFailureMessage", "SignalExpiryMessage", "SignalCloseOutAuthorised"]
            end_signal_state_match = any(end_signal_state.lower() in vars['update_type'].lower() for end_signal_state in end_signal_states)

            if end_signal_state_match and vars['target_order_executed'] == "yes":
                logger.debug("Reached final update messages expected, closing signal")
                return task.complete({"signal_complete": True})
            elif end_signal_state_match and vars['target_order_executed'] == "no":
                return task.bpmn_error("510", "Final update, but failed order", {"close_position": True})

            if vars['target_order_timeout'] == "yes":
                logger.warn('Target ordering process timeout')
                logger.warn('Closing the process because we want to close out unknown state')
                #logger.debug('Not failing out, future orders may succeed, and we definitely want to close out position')
                return task.bpmn_error("510", "Target Ordering Timeout", {"close_position": True})
            elif vars['target_order_failure'] == "yes":
                logger.warn('Target ordering process failed')
                return task.bpmn_error("510", "Target Ordering Failure", {"close_position": True})
            elif vars['target_order_executed'] == "yes":
                logger.debug(f"Target ordering process success for - {vars['update_type']}")
                try:
                    if vars['target_num'] == "A":
                        logger.debug("all targets reached")
                        return task.complete({"signal_complete": True})
                    elif int(vars['target_num']) == 0:
                        logger.debug("closeout situtation should have been handled, forcing it now")
                        return task.complete({"close_position": True, "signal_complete": False})
                    elif int(vars['target_num']) >= int(vars['num_targets']) or int(vars['target_num']) >= int(config['targets']['max_targets_to_process']):
                        logger.debug("this concludes the number of targets that needed to process")
                        logger.debug(f"Current Target Number - {vars['target_num']}")
                        logger.debug(f"Total Signal Targets - {vars['num_targets']}")
                        logger.debug(f"Max Config Targets - {config['targets']['max_targets_to_process']}")
                        return task.complete({"close_position": False, "signal_complete": True, "target_order_executed": True})
                    else:
                        logger.debug("Expecting more updates, resetting signal to waiting for updates")
                        return task.complete({"signal_complete": False})
                except Exception:
                    logger.error(f"Exception determining signalEnd")
                    logger.error(traceback.format_exc())
            else:
                return task.bpmn_error("510", "fell through decision logic", {"signal_complete": end_signal})
        else:
            logger.error(f"Signal not in DB")
            return task.complete({"signal_complete": True})
    except Exception:
        logger.error(f"Exception fetching signal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("502", "Exception fetching signal", {"exception": traceback.format_exc()})

def handle_AssessSignalPerformance(task: ExternalTask):
    logger.trace(f"handle_AssessSignalPerformance - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)
    logger.debug("Implementation incomplete")
    logger.debug('Calculate from the DB the performance of the buy versus the sells, probably need a new table')
    logger.debug('Also check remaining balance (DEFINITELY!), because it should be basically below min notional')
    logger.debug('If there is a remainder above min notional at this point, and if there are no other open position')
    logger.debug('Then exit the position')

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        updates = logic.fetch_related_updates(str(task.get_process_instance_id()))
        if sig and updates['success']:
            logger.trace(f"Signal in DB")
            logger.debug(f"{sig}")
            logger.debug(f"Number of updates in DB - {len(updates['updates'])}")
            logger.debug(f"{updates}")
            logger.debug("REVIEW THE INFORMATION AND FIGURE OUT WHAT YOU WANT TO SUMMARISE")
            new_perf_result = logic.new_performance_record(sig)
            if new_perf_result['success']:
                logger.debug("Storing new performance record fine")
                perf_entry_result = logic.populate_entry_performance(new_perf_result['id'], sig, vars)
                if perf_entry_result['success']:
                    logger.debug("entry performance calcs fine")
                    perf_target_result = logic.populate_target_performance(new_perf_result['id'], updates['updates'], vars)
                    if perf_target_result['success']:
                        logger.debug("Target performance calcs fine")
                        return task.complete({"performance_assessment_success": True, "performance_assessment_id": new_perf_result['id']})
                    else:
                        logger.error("Issue with target performance calc")
                        return task.bpmn_error("511", "Issue calculating target performance", {"performance_assessment_success": False})
                else:
                    logger.error("entry calcs error")
                    return task.bpmn_error("511", "Issue calculating entry performance", {"performance_assessment_success": False})
            else:
                logger.error("Issue creating new perf record")
                time.sleep(20)
                return task.bpmn_error("511", "Issue creating new performance record", {"performance_assessment_success": False})
        else:
            logger.error(f"Missing update information")
            return task.bpmn_error("511", "Missing information", {"performance_assessment_success": False})
    except Exception:
        logger.error(f"Exception Missing update information")
        logger.error(traceback.format_exc())
        return task.bpmn_error("511", "Exception fetching signal", {"performance_assessment_success": False, "exception": traceback.format_exc()})

def handle_FinaliseFailedSignalPositions(task: ExternalTask):
    logger.trace(f"handle_FinaliseFailedSignalPositions - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig and vars['close_position'] == "yes":
            logger.info("This is not completed implemented yet, need to fetch wallet, check balance, and check the executed qty's")
            logger.info("For now it is perform a 'stoploss' manouver")
            time.sleep(5)
            if float(sig['funding_allocated']) > 0.0:
                logger.info(f"Possible remaining position after error - CREATE SELL ORDER")
                logger.info(f"Funding allocated - {sig['funding_allocated']}")
                result = logic.place_market_sell_order(vars['tracking_number'], "SignalCloseOutAuthorised", vars['pair'], vars['entry_price'] ,sig['funding_allocated'])
                if result['success']:
                    logger.debug("Position closed")
                    logger.debug(f"{result}")
                    return task.complete({"signal_complete": True})
                else:
                    logger.error(f"{result}")
                    return task.bpmn_error("514", "Error handle_FinaliseFailedSignalPositions", {"error": "Issue closing position"})
            else:
                logger.error("Should not be possible, missing variables, and or no funding")
                return task.bpmn_error("514", "Error handle_FinaliseFailedSignalPositions", {"error": "Insuffient variable data to create order, entry_price, funding_allocated"})
        else:
            logger.error(f"Signal not found in DB, or close_position is not set by human operator")
            return task.bpmn_error("514", "Signal not found in DB", vars)
    except Exception:
        logger.error(f"Exception handle_FinaliseFailedSignalPositions")
        logger.error(traceback.format_exc())
        return task.bpmn_error("514", "Exception handle_FinaliseFailedSignalPositions", {"exception": traceback.format_exc()})

def handle_CloseOutSignal(task: ExternalTask):
    logger.trace(f"handle_CloseOutSignal - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.trace(vars)

    ## Handle remaining balance if necessary as well

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        if sig['qty_remaining'] == 0.0 and sig['status'] == 'AllTargetsReachedMessage_order_complete' and vars['performance_assessment_success']:
            logger.info("This signal passed all targets, and passed perfectly through the system, archiving without review")
            return task.complete({"signal_complete": True, "auto_archive": True})
        else:
            logger.info(f"This signal was not 100% success, but did reach end, submitting for review")
            return task.complete({"signal_complete": True, "auto_archive": False})
    except Exception:
        logger.error(f"Exception handle_CloseOutSignal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("543", "Exception handle_CloseOutSignal", {"exception": traceback.format_exc()})

def handle_ArchiveSignal(task: ExternalTask):
    logger.trace(f"handle_ArchiveSignal - {task.get_summary()}")
    logger.trace(pformat(task))
    vars = task.get_variables()

    logger.info(vars)

    try:
        sig = logic.fetch_signal(vars['signal_id'])
        logger.info("Signal archived, you now have to use the DB to review performance")
        time.sleep(10)
        # Put archival logic you want here, pretty much i think we should dump the vars into a table, so we can prune camunda
        return task.complete()
    except Exception:
        logger.error(f"Exception handle_ArchiveSignal")
        logger.error(traceback.format_exc())
        return task.bpmn_error("515", "Exception handle_ArchiveSignal", {"exception": traceback.format_exc()})
