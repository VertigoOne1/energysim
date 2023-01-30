import re, traceback, os
from modules.logger import setup_custom_logger
from envyaml import EnvYAML
from pprint import pformat

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

## Takes something like BTC/TTH and makes it BTCTTH, TTH, BTC, lowercase and uppercase versions as necessary for the various REST/WS endpoints
def split_market_pair(pair):
    split = {}
    split["original_pair"] = pair
    base_symbol = "BTC"
    try:
        split["condensed_pair"] = (re.sub("[^0-9a-zA-Z]+", "", pair))
        split["condensed_lower_pair"] = (re.sub("[^0-9a-zA-Z]+", "", pair)).lower()
        split["condensed_upper_pair"] = (re.sub("[^0-9a-zA-Z]+", "", pair)).upper()
        if pair and "/" in pair:
            split["trade_symbol"] = (pair.split("/"))[0]
            split["base_symbol"] = (pair.split("/"))[1]
        else:
            logger.warn(f"Pair received is not a slashed pair, splitting by assuming base BTC! - {pair}")
            if pair and base_symbol in pair:
                logger.warn(f"Trying split by {base_symbol}")
                pos = pair.index(base_symbol)
                split["base_pos"] = pos
                if pos > 0:
                    split["trade_symbol"] = pair[:pos]
                    split["base_symbol"] = pair[pos:]
                elif pos == 0:
                    split["trade_symbol"] = pair[:len(base_symbol)]
                    split["base_symbol"] = pair[len(base_symbol):]
                else:
                    logger.error(f"The location of the base symbol is not making sense")
                    logger.error(pformat(split))
                logger.trace(f"trade - {split['trade_symbol']} - base - {split['base_symbol']}")
            elif pair and base_symbol.lower() in pair:
                logger.debug("Lowercase variant.. you monster")
                logger.warn("Trying split by {base_symbol.lower()}")
                pos = pair.index(base_symbol.lower())
                split["base_pos"] = pos
                if pos > 0:
                    split["trade_symbol"] = pair[:pos]
                    split["base_symbol"] = pair[pos:]
                elif pos == 0:
                    split["trade_symbol"] = str(pair[:len(base_symbol)]).upper()
                    split["base_symbol"] = str(pair[len(base_symbol):]).upper()
                else:
                    logger.error("The location of the base symbol is not making sense")
                    logger.error(pformat(split))
                logger.trace(f"trade - {split['trade_symbol']} - base - {split['base_symbol']}")
            else:
                logger.error(f"Base symbol - {base_symbol} not in pair string, this is not supported")
                split["trade_symbol"] = "NA"
                split["base_symbol"] =  "NA"
        split["split_upper_pair"] = split["trade_symbol"].upper() + "/" + split["base_symbol"].upper()
        split["split_lower_pair"] = split["trade_symbol"].lower() + "/" + split["base_symbol"].lower()
    except Exception as e:
        logger.error(e, exc_info=True)
    return split

def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = str(getattr(row, column.name))
    return d

## Checks if something is float
def is_float(value):
    if (isinstance(value, float)):
        return True
    try:
        float(value)
        return True
    except:
        return False

## Turns anything into float, or to 0.0
def str_to_float(str_float):
    # logger.trace(f"Parsing str to float - {str_float}")
    floated = float(0.0)
    if (isinstance(str_float, float)):
        return str_float
    else:
        try:
            if is_float(str_float):
                floated = float(str_float)
                return floated
            else:
                logger.warn("Number was not floatable, return 0.0")
                return float(0.0)
        except:
            logger.error(f"Exception - number was not floatable - {str_float}")
            return float(0.0)

## Turns a str percentage into a float
def percent_to_float(str_float):
    logger.trace(f"Parsing percent to float - {str_float}")
    str_clean = str(str_float.strip('%'))
    floated = float(0.0)
    try:
        if is_float(str_clean):
            floated = float(str_clean)/100
            return floated
        else:
            logger.error(f"Number was not floatable - {str_float}")
            return float(0.0)
    except:
        logger.error(f"Exception - percent was not floatable - {str_float}")
        return float(0.0)

## Takes an array of numbers and turn them into array of floats
def targets_to_float(targets):
    logger.trace("Parsing array to float - " + str(pformat(targets)))
    floated = float(0.0)
    floated_array = []
    for str_float in targets:
        if is_float(str_float):
            floated = float(str_float)
            floated_array.append(floated)
        else:
            logger.error("Number was not floatable, bringing zero back")
            floated_array.append(float(0.0))
    logger.trace("Floated Array - " + str(pformat(floated_array)))
    return floated_array

def floaty_sig(sig):
    import json
    try:
        logger.trace(f"Before floaty - {sig}")
        from copy import deepcopy
        newsig = {}
        newsig = deepcopy(sig)
        newsig["entry_high"] = float(newsig["entry_high"])
        newsig["entry_low"] = float(newsig["entry_low"])
        newsig["stoploss"] = float(newsig["stoploss"])
        newsig["risk"] = float(newsig["risk"])
        newsig["targets"] = json.loads(newsig["targets"])
        newt = []
        for t in newsig['targets']:
            newt.append(float(t))
        newsig["targets"] = newt
        logger.trace("Fixed dict")
        logger.trace(pformat(newsig))
        return newsig
    except:
        logger.error(f"Exception - floatable numbers could not be floated - {sig}")
        return {}

def floaty_upd(upd):
    import json
    try:
        logger.trace(f"Before floaty - {upd}")
        from copy import deepcopy
        newupd = {}
        newupd = deepcopy(upd)
        try:
            newupd["target_price"] = float(newupd["target_price"])
        except:
            logger.error("target_price issue")
        try:
            newupd["signal_entry_price"] = float(newupd["signal_entry_price"])
        except:
            logger.error("signal_entry_price issue")
        try:
            newupd["next_target_price"] = float(newupd["next_target_price"])
        except:
            logger.error("next_target_price issue")
        try:
            newupd["next_stoploss_price"] = float(newupd["next_stoploss_price"])
        except:
            logger.error("next_stoploss_price issue")
        try:
            newupd["actual_qty_sold"] = float(newupd["actual_qty_sold"])
        except:
            logger.error("actual_qty_sold issue")
        try:
            newupd["planned_qty"] = float(newupd["planned_qty"])
        except:
            logger.error("planned_qty issue")
        newupd['measured_profit_percentage'] = float(newupd['measured_profit_percentage'])
        logger.trace(pformat(newupd))
        return newupd
    except:
        logger.error(f"Exception - floatable numbers could not be floated - {upd}")
        return {}

def floaty_entry(entry):
    import json
    try:
        logger.trace(f"Before floaty - {entry}")
        from copy import deepcopy
        newent = {}
        newent = deepcopy(entry)
        newent["entry_high"] = float(newent["entry_high"])
        newent["entry_low"] = float(newent["entry_low"])
        newent["entry_actual"] = float(newent["entry_actual"])
        newent["last_price"] = float(newent["last_price"])
        newent["success"] = True
        logger.trace("Fixed dict")
        logger.trace(pformat(newent))
        return newent
    except:
        logger.error(f"Exception - floatable numbers could not be floated - {entry}")
        return {"success": False}

def tupleit(result):
    from collections import namedtuple

    Record = namedtuple('Record', result.keys())
    logger.trace(pformat(Record))
    logger.trace(f"Length - {len(result)}")
    records = [Record(*r) for r in result.fetchall()]
    return records

# Calculates a new number by rounding to the modulo and adding the mod until it is a "full number"
def qty_mod(qty, min_lot_size):
    import time, decimal
    # Rounding up to 8 points first
    qty_rounded = decimal.Decimal(float(f"{qty:.8f}"))
    rounded_min_lot_size = decimal.Decimal(round(float(f"{min_lot_size:.8f}"),8))
    logger.debug(f"Before - {qty} - After - {qty_rounded}")
    try:
        logger.debug(f"Input Qty - {qty}")
        logger.debug(f"Rounded Qty - {qty_rounded}")
        logger.debug(f"Minimum Notional - {min_lot_size}")
        logger.debug(f"Rounded Minimum Notional - {rounded_min_lot_size}")
        rem = decimal.Decimal(qty_rounded) % decimal.Decimal(rounded_min_lot_size)
        rem = decimal.Decimal(f"{rem:.8f}")
        new_qty = decimal.Decimal(qty_rounded) - decimal.Decimal(rem)
        new_qty = decimal.Decimal(f"{new_qty:.8f}")
        logger.debug(f"New Qty - {qty_rounded} mod {rounded_min_lot_size} = {rem} --> {qty_rounded} - {rem} = {new_qty}")
        new_rem = decimal.Decimal(f"{decimal.Decimal(new_qty) % decimal.Decimal(rounded_min_lot_size):.8f}")
        logger.debug(f"Double check - {new_qty} mod {round(rounded_min_lot_size,8)} = {new_rem} -> should be zero")
        if new_rem > 0.0:
            logger.debug(f"New remainder - {new_qty} - {new_rem} - {rounded_min_lot_size}")
            final_qty = decimal.Decimal(f"{decimal.Decimal(new_qty) + decimal.Decimal(new_rem)}")
            logger.debug(f"Adding new remainder {new_qty} + {new_rem} = {final_qty}")
            again = round(decimal.Decimal(final_qty) % decimal.Decimal(round(rounded_min_lot_size,8)),8)
            if  again > 0.0:
                logger.error(f"NOOOOOOOOOOOOOOOOO - {again}")
                time.sleep(60)
            else:
                logger.debug(f"Looks good - Clean Qty - remainder - {again} {decimal.Decimal(final_qty)}")
                lot = float(f"{rounded_min_lot_size:.8f}")
                q = float(f"{final_qty:.8f}")
                return dict(success = True, qty = q, min_lot_size = lot, error = "")
        else:
            final_qty = new_qty
            logger.debug(f"No final remainder - {new_qty} = {final_qty}")
            lot = float(f"{rounded_min_lot_size:.8f}")
            q = float(f"{final_qty:.8f}")
            return dict(success = True, qty = q, min_lot_size = lot, error = "")
    except Exception:
        logger.error(f"Exception calcing qty_modulus for min_notional")
        logger.error(traceback.format_exc())
        return dict(success = False, qty = qty_rounded, min_lot_size = rounded_min_lot_size, error = traceback.format_exc())