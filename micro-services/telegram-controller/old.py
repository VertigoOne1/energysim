#!/bin/python3
from telethon import TelegramClient, events, sync
import logging; logging.basicConfig(level=logging.INFO)
import re, json, time, os
from pprint import pformat

# Next up
# Code an update splitter, that monitors new and throws it into the different directories
# targetChaser is first, as soon as it gets a target reached, create a market sell order for the position
    # - if there is a buy order, cancel it, it missed the boat, failed, but no loss
    # - if there is a balance, sell oco percentage 1 or min-buy
# stopLoss does the same
    # - if there is a buy, cancel, missed
    # - sell balance
# closeOut
    # - cancel any buy orders
    # - cancel any sell orders


# REWRITE THE MATCHER TO FOCUS ON EACH LINE INDIVIDUALLY. THE FUCKER STARTED SWAPPING AROUND LINES


msg_classified_signal_directory = './msg2trade_result/classified/signal'
msg_classified_update_directory = './msg2trade_result/classified/update'
msg_unclassified_directory = './msg2trade_result/unclassified'
new_signals_directory = './chatTrade/signals/new'
socket_buy_new = './sockBuy/new'
new_updates_directory = './chatTrade/updates/new'
db_version_directory = './chat2dbTrade/signals/new'

class PABS_Signal:
    "PABS Signal"
    def __init__(self, avg="NA", profit="NA", risk="NA", pair="NA", entry_low="NA", entry_high="NA", targets = ["NA"], stoploss = "NA", success = False, date_inserted = "NA", timestamp_inserted=time.time(), tracking_number = "NA", raw_message = "NA"):
        self.avg = avg
        self.profit = profit
        self.risk = risk
        self.pair = pair
        self.entry_low = entry_low
        self.entry_high = entry_high
        self.targets = targets
        self.stoploss = stoploss
        self.success = success
        self.date_inserted = date_inserted
        self.timestamp_inserted = timestamp_inserted
        self.tracking_number = tracking_number
        self.raw_message = raw_message

        self.buy_zone_words = ["Accumulation", "Accumulate", "Acquire", "Get some", "Get between", "Entry", "Scalp", "scalp", "Gain", "Buy", "Take point", "Enter", "Grab dip", "Get ", "Grab in", "Grab ", "Grabbing", "Take around", "Take zone", "Take area", "Take in", "Take it", "Take some around", "Take between", "Take :", "Take  :", "Take some", "Take Some", "take some", "Buying some", "Buying ", "buying ", "Take price", "Take Price", "take price", "Buy range", "Buy Range", "Buying the dip", "Take the dip", "Take range"]
        self.stop_loss_words = ["SL", "stop", "Stop loss", "Stop", "Stoploss"]
        self.sell_words = ["Sell", "Target", "Targets", "TPS", "Take Profits", "TPs", "Sells", "TP "]

    def is_integer_num(self, n):
        if isinstance(n, int):
            return True
        if isinstance(n, float):
            return n.is_integer()
        return False

    def normalise_num(self, n):
        if self.is_integer_num(float(n)):
            logging.debug("Normalising")
            nw = float(n) / 100000000
            normalised = (f'{nw:1.8f}')
        else:
            normalised = (f'{float(n):1.8f}')
        return normalised

    def toJSON(self):
            return json.dumps(self, default=lambda o: o.__dict__,
                sort_keys=True, indent=4)

    def process(self, msg=["NA"]):
        messagelines = msg
        raw_message = msg
        logging.debug(messagelines[0])
        logging.debug(messagelines[1])
        if "New signal" in messagelines[0]:
            logging.debug("PABS Signal Start Found")
            if "/s" in messagelines[len(messagelines)-1]:
                logging.debug("PABS Signal End Found")
                if "Avg" in messagelines[3]:
                    avg_start = messagelines[3].find("Avg: buy ") + 9
                    avg_end = messagelines[3].find(" from top")
                    avg = messagelines[3][avg_start:avg_end]
                    profit_start = messagelines[3].find(" profit ") + 8
                    profit_end = messagelines[3].find(". Risk: ")
                    profit = messagelines[3][profit_start:profit_end]
                    risk_start = messagelines[3].find(". Risk: ") + 8
                    risk_end = len(messagelines[3]) - 1
                    risk = messagelines[3][risk_start:risk_end]
                else:
                    avg = "NA"
                    risk = "99"
                    profit = "NA"
                if "www.binance.com" in (messagelines[2]):
                    pair_start = 0
                    pair_end = messagelines[2].find(" (https")
                    pair = messagelines[2][pair_start:pair_end]
                elif "ideas" in (messagelines[2]):
                    pair_start = 0
                    pair_end = messagelines[2].find(": ideas")
                    pair = messagelines[2][pair_start:pair_end]
                else:
                    logging.debug("issue with binance and ideas, lets take a shot at using the : on;y")
                    pair_end = messagelines[2].find(": ")
                    pair = messagelines[2][pair_start:pair_end]
                    logging.debug("Pair: " + str(pair))
                logging.debug(messagelines[6])
                failed_line_7 = False 
                buy_zone_string_match = any(buy_zone_word in messagelines[6] for buy_zone_word in self.buy_zone_words)
                if buy_zone_string_match:
                    buy_string = messagelines[6].replace(" ", "")
                    buy_string = buy_string.replace("::", ":")
                    buy_string = buy_string.replace("=", ":")
                    buy_string = buy_string.replace("-", ":")
                    buy_string = buy_string.replace("—", ":")
                    buy_string = buy_string.replace("—", ":")
                    buy_string = (re.sub("[^0-9.\:]+", "", buy_string))
                    logging.debug(buy_string)
                    entry_values = buy_string.split(":")
                    for vals in entry_values:
                        logging.debug("Entry Values - " + str(vals))
                    entry_low = entry_values[1]
                    entry_high = entry_values[2]
                else:
                    logging.error("Buy zone string match failed on line 7 - " + messagelines[6])
                    failed_line_7 = True
                logging.debug(messagelines[5])
                if failed_line_7:
                    buy_zone_string_match = any(buy_zone_word in messagelines[5] for buy_zone_word in self.buy_zone_words)
                    if buy_zone_string_match:
                        buy_string = messagelines[5].replace(" ", "")
                        buy_string = buy_string.replace("::", ":")
                        buy_string = buy_string.replace("=", ":")
                        buy_string = buy_string.replace("-", ":")
                        buy_string = buy_string.replace("—", ":")
                        buy_string = buy_string.replace("—", ":")
                        buy_string = (re.sub("[^0-9.\:]+", "", buy_string))
                        logging.debug(buy_string)
                        entry_values = buy_string.split(":")
                        for vals in entry_values:
                            logging.debug("Entry Values - " + str(vals))
                        entry_low = entry_values[1]
                        entry_high = entry_values[2]
                    else:
                        logging.error("Buy zone string match failed on line 6 - " + messagelines[5])
                sell_word_line_start = 7
                if failed_line_7:
                    sell_word_line_start = 6
                logging.debug("Sell word start - " + str(sell_word_line_start))
                for i in range(sell_word_line_start,len(messagelines)):
                    logging.debug("Sell Range Line - " + messagelines[i])
                    stop_word_match = any(stop_loss_word in messagelines[i] for stop_loss_word in self.stop_loss_words)
                    if stop_word_match:
                        stop_word_line_start = i - 1
                    logging.debug("StopLoss - " + str(stop_word_match))
                logging.debug("Profit_Points Start - " + str(sell_word_line_start))
                logging.debug("Profit_Points Stop - " + str(stop_word_line_start))
                targets = stop_word_line_start - sell_word_line_start
                logging.debug("Between - " + str(targets))
                target_lines = []
                if targets < 2:
                    # Suspect single line with all the targets, lets parse that
                    logging.debug(messagelines[7])
                    targets_line = messagelines[7]
                    targets_line = targets_line.replace(" ", ":")
                    targets_line = targets_line.replace("::", ":")
                    targets_line = targets_line.replace("=", ":")
                    targets_line = targets_line.replace("-", ":")
                    targets_line = targets_line.replace("—", ":")
                    targets_line = targets_line.replace("—", ":")
                    targets_filtered = (re.sub("[^0-9.\:]+", "", targets_line))
                    logging.debug(targets_filtered)
                    target_lines = targets_filtered.split(":")
                    target_lines = list(filter(None, target_lines))
                elif targets >=3 and targets <= 4:
                    for i in range(sell_word_line_start + 1,stop_word_line_start + 1):
                        target_string = messagelines[i].replace("  ", " ")
                        target_string = target_string.replace("  ", " ")
                        target_string = target_string.rstrip("\n")
                        target_line_split = target_string.split(" ")
                        val = target_line_split[len(target_line_split) -1 ]
                        logging.debug(val)
                        target_lines.append(val)
                elif targets > 4:
                    logging.error("Ignoring - too many targets " + pair)
                else:
                    logging.error("Ignoring - not making sense - " + pair)
                logging.debug(target_lines)
                sl = messagelines[stop_word_line_start + 1]
                logging.debug(sl)
                sl = sl.replace(" ", "")
                sl = sl.replace("::", ":")
                sl = sl.replace("=", ":")
                sl = sl.replace("-", ":")
                sl = sl.replace("—", ":")
                sl = sl.replace("—", ":")
                sl = (re.sub("[^0-9.\:]+", "", sl))
                sl = (re.sub("[^0-9.]+", "", sl))
                logging.debug(sl)
                # logging.info(messagelines[len(messagelines)])
                last_line = messagelines[len(messagelines)-1]
                tracking_number_start = last_line.find("/s")
                tracking_number_end = last_line.find(", or view all")
                logging.info("Tracking Number - " + last_line[tracking_number_start+1:tracking_number_end])
                tracking_number = last_line[tracking_number_start+1:tracking_number_end]
                if re.findall(r"[^0-9][0-9]{5,8}", tracking_number):
                    logging.info("Matched a standard tracking number, continuing")
                else:
                    tracking_number = "NA"
                # Sometimes the values are in satoshies, need to convert to binance
                normalised_targets = []
                for tg in target_lines:
                    logging.debug(tg)
                    normalised_targets.append(self.normalise_num(tg))
                self.avg = avg
                self.raw_message = raw_message
                self.profit = profit
                self.risk = risk
                self.pair = pair
                try:
                    self.entry_low = self.normalise_num(entry_low)
                    self.entry_high = self.normalise_num(entry_high)
                except:
                    logging.debug("Not setable, defaulting")
                self.targets = normalised_targets
                self.stoploss = self.normalise_num(sl)
                if self.entry_high == "NA" or self.entry_low == "NA":
                    logging.error("Issue with extracting buy zone information")
                    self.success = False
                else:
                    self.success = True
                self.date_inserted = str(time.strftime("%Y%m%d-%H%M%S"))
                self.timestamp_inserted = time.time()
                self.tracking_number = tracking_number
            else:
                logging.debug("Not PABS Signal Message - Inner")
        else:
            logging.debug("Not PABS Signal Message - Outter")

class PABS_Update_Message:
    "PABS Update"

    def __init__(self, tracking_number="NA", signal_decision="NA", profit_percentage="NA", update_type="NA", traded_symbol="NA", target_price="NA", entry_price="NA", signal_entry_time = "NA", stoploss_decision = "NA", next_target_price = "NA", success = False, date_inserted = "NA", timestamp_inserted=time.time(), raw_message = "NA", next_stoploss_price = "NA"):
        self.tracking_number = tracking_number
        self.update_type = update_type
        self.traded_symbol = traded_symbol
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.signal_decision = signal_decision
        self.next_target_price = next_target_price
        self.next_stoploss_price = next_stoploss_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.date_inserted = date_inserted
        self.timestamp_inserted = timestamp_inserted
        self.raw_message = raw_message

        self.first_target_words = ["First target", "Bought at", "Move stoploss if you"]
        self.second_target_words = ["Second target", "Bought at", "Move stoploss if you"]
        self.third_target_words = ["Third target", "Bought at", "Move stoploss if you"]
        self.fourth_target_words = ["Fourth target"]
        self.all_targets_done_words = ["All targets", "All 3 targets done", "All two targets done", "All three targets done", "All four targets done", "All 4 targets done"]
        self.move_stoploss_words = ["Move stoploss"]
        self.only_target_done_words = ["Target", "done", "profit", "Trade closed!"]
        self.touched_stoploss_one_words = ["Touched stoploss", "1 targets done"]
        self.touched_stoploss_two_words = ["Touched stoploss", "2 targets done"]
        self.touched_stoploss_three_words = ["Touched stoploss", "3 targets done"]
        self.touched_stoploss_failed_words = ["Touched stoploss", "Trade closed", "loss"]
        self.signal_at_7_days = ["more than 7 days ago"]

    def is_integer_num(self, n):
        if isinstance(n, int):
            return True
        if isinstance(n, float):
            return n.is_integer()
        return False

    def normalise_num(self, n):
        if self.is_integer_num(float(n)):
            logging.debug("Normalising")
            nw = float(n) / 100000000
            normalised = (f'{nw:1.8f}')
        else:
            normalised = (f'{float(n):1.8f}')
        return normalised

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)

    def processFirstTargetMessage(self,msg="NA"):
        # Update #NEO signal /s15235
        # First target 0.000947 done, +4.3%. Bought at 0.000908 1 d 7 hr ago. Move stoploss if you want at 0.00093.
        messagelines = msg
        success = True
        stoploss_decision = "Move"

        # sell price,
        if "First target" in (messagelines[1]):
            pair_start = messagelines[1].find("First target ") + len("First target ")
            pair_end = messagelines[1].find(" done")
            price1 = messagelines[1][pair_start:pair_end]
            logging.debug(price1)

        # PABS gains,
        if "First target" in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("%. ") + len("%. ")
            gains = messagelines[1][pair_start:pair_end - 2]
            logging.debug(gains)
        if "% profit." in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("% profit. ")
            gains = messagelines[1][pair_start:pair_end + 1]
            logging.debug(gains)

        # PABS entry point
        if "First target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            detect_price = messagelines[1][pair_start:len(messagelines[1])]
            logging.debug(detect_price)
            price_break_up = detect_price.split(" ")
            entry_point = price_break_up[0]
            logging.debug(entry_point)

        # PABS timespan
        if "First target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            pair_end = messagelines[1].rfind(" ago.") +  + len(" ago.")
            detect_timespan = messagelines[1][pair_start:pair_end]
            logging.debug(detect_timespan)
            price_len = len(detect_price.split(" ")[0])
            timespan = detect_timespan[price_len:pair_end]
            logging.debug(timespan)
            try:
                signal_entry_time = str(dateparser.parse(timespan))
            except:
                signal_entry_time = "NA"
            logging.debug(signal_entry_time)

        # PABS next target
        if "First target" in (messagelines[1]):
            pair_start = messagelines[1].rfind(" if you want at ") + len(" if you want at ")
            pair_end = len(messagelines[1]) - 1
            next_stoploss_price = messagelines[1][pair_start:pair_end]
            logging.debug(next_stoploss_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "FirstTargetReached"
        signal_decision = "sell_first_target"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_stoploss_price = next_stoploss_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processSecondTargetMessage(self,msg="NA"):
        #Update #NMR signal /s15255
        #Second target 0.000957 done, +18.15% profit. Bought at 0.00081 2 d 6 hr ago. Move stoploss if you want at 0.0009
        messagelines = msg
        success = True
        stoploss_decision = "Move"

        # sell price,
        if "Second target" in (messagelines[1]):
            pair_start = messagelines[1].find("Second target ") + len("Second target ")
            pair_end = messagelines[1].find(" done")
            price1 = messagelines[1][pair_start:pair_end]
            logging.debug(price1)

        # PABS gains,
        if "Second target" in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("%. ") + len("%. ")
            gains = messagelines[1][pair_start:pair_end - 2]
            logging.debug(gains)
        if "% profit." in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("% profit. ")
            gains = messagelines[1][pair_start:pair_end + 1]
            logging.debug(gains)

        # PABS entry point
        if "Second target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            detect_price = messagelines[1][pair_start:len(messagelines[1])]
            logging.debug(detect_price)
            price_break_up = detect_price.split(" ")
            entry_point = price_break_up[0]
            logging.debug(entry_point)

        # PABS timespan
        if "Second target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            pair_end = messagelines[1].rfind(" ago.") +  + len(" ago.")
            detect_timespan = messagelines[1][pair_start:pair_end]
            logging.debug(detect_timespan)
            price_len = len(detect_price.split(" ")[0])
            timespan = detect_timespan[price_len:pair_end]
            logging.debug(timespan)
            try:
                signal_entry_time = str(dateparser.parse(timespan))
            except:
                signal_entry_time = "NA"
            logging.debug(signal_entry_time)

        # PABS next target
        if "Second target" in (messagelines[1]):
            pair_start = messagelines[1].rfind(" if you want at ") + len(" if you want at ")
            pair_end = len(messagelines[1]) - 1
            next_stoploss_price = messagelines[1][pair_start:pair_end]
            logging.debug(next_stoploss_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "SecondTargetReached"
        signal_decision = "sell_second_target"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_stoploss_price = next_stoploss_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processThirdTargetMessage(self,msg="NA"):
        # Update #PHA signal /s15230
        # Third target 0.00002512 done, +27.58% profit. Bought at 0.00001969 3 d 15 hr ago. Move stoploss if you want at 0.00002405        messagelines = msg
        messagelines = msg
        success = True
        stoploss_decision = "Move"

        # sell price
        if "Third target" in (messagelines[1]):
            pair_start = messagelines[1].find("Third target ") + len("Third target ")
            pair_end = messagelines[1].find(" done")
            price1 = messagelines[1][pair_start:pair_end]
            logging.debug(price1)

        # PABS gains
        if "Third target" in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("%. ") + len("%. ")
            gains = messagelines[1][pair_start:pair_end - 2]
            logging.debug(gains)
        if "% profit." in (messagelines[1]):
            pair_start = messagelines[1].find(" done, ") + len(" done, ")
            pair_end = messagelines[1].find("% profit. ")
            gains = messagelines[1][pair_start:pair_end + 1]
            logging.debug(gains)

        # PABS entry point
        if "Third target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            detect_price = messagelines[1][pair_start:len(messagelines[1])]
            logging.debug(detect_price)
            price_break_up = detect_price.split(" ")
            entry_point = price_break_up[0]
            logging.debug(entry_point)

        # PABS timespan
        if "Third target" in (messagelines[1]):
            pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
            pair_end = messagelines[1].rfind(" ago.") +  + len(" ago.")
            detect_timespan = messagelines[1][pair_start:pair_end]
            logging.debug(detect_timespan)
            price_len = len(detect_price.split(" ")[0])
            timespan = detect_timespan[price_len:pair_end]
            logging.debug(timespan)
            try:
                signal_entry_time = str(dateparser.parse(timespan))
            except:
                signal_entry_time = "NA"
            logging.debug(signal_entry_time)

        # PABS next target
        if "Third target" in (messagelines[1]):
            pair_start = messagelines[1].rfind(" if you want at ") + len(" if you want at ")
            pair_end = len(messagelines[1]) - 1
            next_stoploss_price = messagelines[1][pair_start:pair_end]
            logging.debug(next_stoploss_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "ThirdTargetReached"
        signal_decision = "sell_third_target"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_stoploss_price = next_stoploss_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processOnlyTargetDoneMessage(self,msg="NA"):
        # Update #GTC signal /s15293
        # Target 0.0002208 done. +8.18% profit. Bought at 0.0002041 1 d 17 hr ago. Trade closed!

        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # sell price
        pair_start = messagelines[1].find("Target ") + len("Target ")
        pair_end = messagelines[1].find("done. ")
        price1 = messagelines[1][pair_start:pair_end - 1]
        logging.debug(price1)

        # PABS gains
        pair_start = messagelines[1].find(". +") + len(". +")
        pair_end = messagelines[1].find("% profit ")
        gains = messagelines[1][pair_start:pair_end - 2]
        logging.debug(gains)
        if "% profit." in (messagelines[1]):
            pair_start = messagelines[1].find(". +") + len(". +")
            pair_end = messagelines[1].find("% profit. ")
            gains = messagelines[1][pair_start - 1:pair_end + 1]
            logging.debug(gains)

        # PABS entry point
        pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ")
        pair_end = pair_start + 9
        detect_price = messagelines[1][pair_start:pair_end]
        logging.debug(detect_price)
        entry_point = detect_price
        logging.debug(entry_point)

        # PABS timespan
        pair_start = messagelines[1].find(" Bought at ") + len(" Bought at ") + 10
        pair_end = messagelines[1].find(" ago.")
        timespan = messagelines[1][pair_start:pair_end + 4]
        logging.debug(timespan)
        try:
            signal_entry_time = str(dateparser.parse(timespan))
        except:
            signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "AllTargetsReachedMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processAllTargetsDoneMessage(self,msg="NA"):
        # Update #NMR signal /s15255
        # All 4 targets done, bought at 0.00081 2 d 8 hr ago and hit 0.001233. +52.22% profit. Trade closed!
        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # sell price
        pair_start = messagelines[1].find(" and hit ") + len(" and hit ")
        pair_end = messagelines[1].find(". ")
        price1 = messagelines[1][pair_start:pair_end]
        logging.debug(price1)

        # PABS gains
        pair_start = messagelines[1].find(". +") + len(". +")
        pair_end = messagelines[1].find("% profit ")
        gains = messagelines[1][pair_start:pair_end - 2]
        logging.debug(gains)
        if "% profit." in (messagelines[1]):
            pair_start = messagelines[1].find(". +") + len(". +")
            pair_end = messagelines[1].find("% profit. ")
            gains = messagelines[1][pair_start - 1:pair_end + 1]
            logging.debug(gains)

        # PABS entry point
        pair_start = messagelines[1].find(" bought at ") + len(" bought at ")
        detect_price = messagelines[1][pair_start:len(messagelines[1])]
        logging.debug(detect_price)
        price_break_up = detect_price.split(" ")
        entry_point = price_break_up[0]
        logging.debug(entry_point)

        # PABS timespan
        pair_start = messagelines[1].find(" bought at ") + len(" bought at ")
        pair_end = messagelines[1].find(" ago and ")
        detect_timespan = messagelines[1][pair_start:pair_end]
        logging.debug(detect_timespan)
        price_len = len(detect_price.split(" ")[0])
        timespan = detect_timespan[price_len:pair_end]
        logging.debug(timespan)
        try:
            signal_entry_time = str(dateparser.parse(timespan))
        except:
            signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "AllTargetsReachedMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processStoplossFailedMessage(self,msg="NA"):
        # Update #CELO signal /s15261
        # Touched stoploss 0.00008986, bought at 0.00009673 1 d 2 hr ago. Trade closed, loss -7.1%.
        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # stop loss price
        pair_start = messagelines[1].find("Touched stoploss ") + len("Touched stoploss ")
        pair_end = messagelines[1].find(", b")
        price1 = messagelines[1][pair_start:pair_end]
        logging.debug(price1)

        # PABS losses
        pair_start = messagelines[1].find("loss -") + len("loss -")
        pair_end = messagelines[1].find("%.")
        gains = messagelines[1][pair_start - 1:pair_end + 1]
        logging.debug(gains)

        # PABS entry point
        pair_start = messagelines[1].find(" bought at ") + len(" bought at ")
        detect_price = messagelines[1][pair_start:len(messagelines[1])]
        logging.debug(detect_price)
        price_break_up = detect_price.split(" ")
        entry_point = price_break_up[0]
        logging.debug(entry_point)

        # PABS timespan
        pair_start = messagelines[1].find(" bought at ") + len(" bought at ")
        pair_end = messagelines[1].find(" ago. ")
        detect_timespan = messagelines[1][pair_start:pair_end]
        logging.debug(detect_timespan)
        price_len = len(detect_price.split(" ")[0])
        timespan = detect_timespan[price_len:pair_end]
        logging.debug(timespan)
        try:
            signal_entry_time = str(dateparser.parse(timespan))
        except:
            signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "StoplossReachedMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processStoplossOneMessage(self,msg="NA"):
        # Update #MIR signal /s15212
        # Touched stoploss 0.0001151. Trade closed with 1 targets done, +2.24% profit.
        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # Stoploss price
        pair_start = messagelines[1].find("Touched stoploss ") + len("Touched stoploss ")
        pair_end = messagelines[1].find(". T")
        price1 = messagelines[1][pair_start:pair_end]
        logging.debug(price1)

        # PABS gains
        pair_start = messagelines[1].find("1 targets done, ") + len("1 targets done, ")
        pair_end = messagelines[1].find("% profit")
        gains = messagelines[1][pair_start:pair_end - 1]
        logging.debug(gains)

        # PABS entry point
        entry_point = "NA"
        logging.debug(entry_point)

        # PABS timespan
        signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "LimitedFailureMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processStoplossTwoMessage(self,msg="NA"):
        # Update #MIR signal /s15212
        # Touched stoploss 0.0001151. Trade closed with 1 targets done, +2.24% profit.
        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # Stoploss price
        pair_start = messagelines[1].find("Touched stoploss ") + len("Touched stoploss ")
        pair_end = messagelines[1].find(". T")
        price1 = messagelines[1][pair_start:pair_end]
        logging.debug(price1)

        # PABS gains
        pair_start = messagelines[1].find("2 targets done, ") + len("2 targets done, ")
        pair_end = messagelines[1].find("% profit")
        gains = messagelines[1][pair_start:pair_end - 1]
        logging.debug(gains)

        # PABS entry point
        entry_point = "NA"
        logging.debug(entry_point)

        # PABS timespan
        signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "LimitedFailureMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processStoplossThreeMessage(self,msg="NA"):
        # Update #MIR signal /s15212
        # Touched stoploss 0.0001151. Trade closed with 1 targets done, +2.24% profit.
        messagelines = msg
        success = True
        stoploss_decision = "terminate"

        # Stoploss price
        pair_start = messagelines[1].find("Touched stoploss ") + len("Touched stoploss ")
        pair_end = messagelines[1].find(". T")
        price1 = messagelines[1][pair_start:pair_end]
        logging.debug(price1)

        # PABS gains
        pair_start = messagelines[1].find("3 targets done, ") + len("3 targets done, ")
        pair_end = messagelines[1].find("% profit")
        gains = messagelines[1][pair_start:pair_end - 1]
        logging.debug(gains)

        # PABS entry point
        entry_point = "NA"
        logging.debug(entry_point)

        # PABS timespan
        signal_entry_time = "NA"
        logging.debug(signal_entry_time)

        # PABS next target
        next_target_price = "NA"
        logging.debug(next_target_price)

        target_price = price1
        entry_price = entry_point
        profit_percentage = gains
        update_type = "LimitedFailureMessage"
        signal_decision = "sell_signal_balance"

        self.update_type = update_type
        self.target_price = target_price
        self.entry_price = entry_price
        self.signal_entry_time = signal_entry_time
        self.stoploss_decision = stoploss_decision
        self.next_target_price = next_target_price
        self.success = success
        self.profit_percentage = profit_percentage
        self.signal_decision = signal_decision

    def processOldSignalMessage(self,msg="NA"):
        update_type = "SignalExpiryMessage"
        signal_decision = "sell_signal_balance"
        success = True
        stoploss_decision = "terminate"
        self.update_type = update_type
        self.signal_decision = signal_decision
        self.success = True
        self.stoploss_decision = stoploss_decision

    def process(self, msg=["NA"]):
        messagelines = msg
        logging.debug(messagelines[0])
        timestamp_inserted = time.time()
        date_inserted = str(time.strftime("%Y%m%d-%H%M%S"))
        raw_message = msg
        if "Update #" in messagelines[0] and " signal " in messagelines[0]:
            logging.info("PABS update message detected")
            if (re.findall(r"[^0-9][0-9]{5,8}", messagelines[0])):
                logging.debug("Matched a standard tracking number")
                tracking_number = re.findall(r"[^0-9][0-9]{5,8}", messagelines[0])[0]
                logging.info("Tracking Number: " + str(tracking_number))
            first_line_split = messagelines[0].split(' ')
            for word in first_line_split:
                logging.debug(word)
                if (re.findall(r"^#", word)):
                    traded_symbol = word[1:len(word)]
            second_line_split = messagelines[1].split(' ')
        old_signal_match = all(signal_7 in messagelines[1] for signal_7 in self.signal_at_7_days)
        first_target_match = all(first in messagelines[1] for first in self.first_target_words)
        second_target_match = all(second in messagelines[1] for second in self.second_target_words)
        third_target_match = all(third in messagelines[1] for third in self.third_target_words)
        fourth_target_match = all(fourth in messagelines[1] for fourth in self.fourth_target_words)
        all_targets_done_match = any(word in messagelines[1] for word in self.all_targets_done_words)
        touched_stoploss_failed_match = all(stop in messagelines[1] for stop in self.touched_stoploss_failed_words)
        touched_stoploss_three_match = all(stop in messagelines[1] for stop in self.touched_stoploss_three_words)
        touched_stoploss_two_match = all(stop in messagelines[1] for stop in self.touched_stoploss_two_words)
        touched_stoploss_one_match = all(stop in messagelines[1] for stop in self.touched_stoploss_one_words)
        only_target_done_words_match = all(one in messagelines[1] for one in self.only_target_done_words)
        if old_signal_match:
            logging.info("Message is notification to do something after 7 days")
            self.processOldSignalMessage(messagelines)
        elif first_target_match:
            logging.info("Message is notification for hitting the first_target_match")
            self.processFirstTargetMessage(messagelines)
        elif second_target_match:
            logging.info("Message is notification for hitting the second_target_match")
            self.processSecondTargetMessage(messagelines)
        elif third_target_match:
            self.processThirdTargetMessage(messagelines)
            logging.info("Message is notification for hitting the third_target_match")
        elif fourth_target_match:
            logging.info("Message is notification for hitting the fourth_target_match")
        elif all_targets_done_match:
            logging.info("Message is notification for hitting the all_targets_done_match")
            self.processAllTargetsDoneMessage(messagelines)
        elif all_targets_done_match:
            logging.info("Message is notification for hitting the all_targets_done_match")
            self.processAllTargetsDoneMessage(messagelines)
        elif only_target_done_words_match:
            logging.info("Message is notification for hitting the only_target_done_words_match")
            self.processOnlyTargetDoneMessage(messagelines)
        elif touched_stoploss_three_match:
            logging.info("Message is notification for hitting the touched_stoploss_three_match")
            self.processStoplossThreeMessage(messagelines)
        elif touched_stoploss_two_match:
            logging.info("Message is notification for hitting the touched_stoploss_two_match")
            self.processStoplossTwoMessage(messagelines)
        elif touched_stoploss_one_match:
            logging.info("Message is notification for hitting the touched_stoploss_one_match")
            self.processStoplossOneMessage(messagelines)
        elif touched_stoploss_failed_match:
            logging.info("Message is notification for hitting the touched_stoploss_failed_match")
            self.processStoplossOneMessage(messagelines)
        else:
            logging.info("Unclassified Update Message")
            success = False
            tracking_number = "NA"
            date_inserted = "NA"
            timestamp_inserted = "NA"
            traded_symbol = "NA"
            self.success = success
        self.raw_message = raw_message
        self.tracking_number = tracking_number
        self.date_inserted = date_inserted
        self.timestamp_inserted = timestamp_inserted
        self.traded_symbol = traded_symbol

def chatTrader(message_data):
    messagelines = []
    logging.debug("String newline split")
    messagelines = str(message_data).splitlines()
    for lines in messagelines:
        logging.debug(lines)
    message = {}
    message["message_type"] = "unknown"
    message["parse_success"] = False
    logging.debug("String newline split")
    message_raw = PABS_Signal()
    message_raw.process(messagelines)
    if message_raw.success:
        logging.info("Signal Detected")
        message = json.loads(message_raw.toJSON())
        message.pop('sell_words')
        message.pop('stop_loss_words')
        message.pop('buy_zone_words')
        message["message_type"] = "new_signal"
        message["parse_success"] = True
        logging.info(pformat(message))
    else:
        logging.debug("Message not Signal")
    message_raw = PABS_Update_Message()
    message_raw.process(messagelines)
    if message_raw.success:
        logging.debug("Update Detected")
        message = json.loads(message_raw.toJSON())
        message.pop('first_target_words')
        message.pop('second_target_words')
        message.pop('third_target_words')
        message.pop('fourth_target_words')
        message.pop('all_targets_done_words')
        message.pop('move_stoploss_words')
        message.pop('only_target_done_words')
        message.pop('touched_stoploss_one_words')
        message.pop('touched_stoploss_two_words')
        message.pop('touched_stoploss_three_words')
        message.pop('touched_stoploss_failed_words')
        message.pop('signal_at_7_days')
        message["message_type"] = "update_message"
        message["parse_success"] = True
        logging.info(pformat(message))
    else:
        logging.debug("Message is not an update")
    # Finally catch for catagorisation
    if not message["parse_success"]:
        logging.info("Message not figured out")
        filename = "PABS_UNCLASS_MSG_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
        with open(os.path.join(msg_unclassified_directory, filename), 'w') as text_file:
            text_file.write(message_data)
    elif message["parse_success"]:
        logging.info("Message Identified")
        if message["message_type"] == "new_signal":
            filename = "PABS_SIG_MSG_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
            with open(os.path.join(msg_classified_signal_directory, filename), 'w') as text_file:
                text_file.write(message_data)
            filename = "PABS_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".json"
            logging.info(filename)
            output = open(os.path.join(new_signals_directory, filename), "w")
            output.write(json.dumps(message))
            output.close()
            logging.info('Split out the file for DB version')
            filename = "PABS_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".json"
            output = open(os.path.join(db_version_directory, filename), "w")
            output.write(json.dumps(message))
            output.close()
            logging.info('Split out to websocket version')
            filename = "PABS_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".json"
            output = open(os.path.join(socket_buy_new, filename), "w")
            output.write(json.dumps(message))
            output.close()
        elif message["message_type"] == "update_message":
            filename = "PABS_UPD_MSG_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
            with open(os.path.join(msg_classified_update_directory, filename), 'w') as text_file:
                text_file.write(message_data)
            filename = "PABS_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".json"
            logging.info(filename)
            output = open(os.path.join(new_updates_directory, filename), "w")
            output.write(json.dumps(message))
            output.close()
    else:
        logging.error("what..")
        logging.error(pformat(message))
        exit(1)
    logging.info("Now do something!")
    logging.info(pformat(message))

with TelegramClient('name', api_id, api_hash, timeout=100) as client:
    @client.on(events.NewMessage(chats='PABS.VIP'))
    async def check_octo(event):
        filename = "PABS_RAW_MSG" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
        with open("./raw_message/" + filename, 'w') as text_file:
            text_file.write(event.raw_text)
        chatTrader(event.raw_text)
        if 'Update' in event.raw_text[0:10]:
            filename = "PABS_UPDATE_MSG_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
            with open("./update_msg/" + filename, 'w') as text_file:
                    text_file.write(event.raw_text)
        elif 'Signal' in event.raw_text and ('new' in event.raw_text[0:5] or 'New' in event.raw_text[0:5]):
            try:
                logging.info(time.strftime("%Y%m%d-%H%M%S"))
                logging.info(str(time.time()))
                logging.debug("PABS Channel Message - raw")
                logging.info(event.raw_text)
                parsemessage = PABS_Signal()
                messagelines = []
                logging.debug("String newline split")
                messagelines = str(event.raw_text).splitlines()
                for lines in messagelines:
                    logging.debug(lines)
                logging.debug("String newline split")
                parsemessage.process(messagelines)
                if parsemessage.success:
                    filename = "PABS_RAW_SIGNAL" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
                    with open("./raw_signals/" + filename, 'w') as text_file:
                        text_file.write(event.raw_text)
                    logging.info(vars(parsemessage))
                    filename = "PABS_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".json"
                    logging.info(filename)
                    signal_dict = json.loads(parsemessage.toJSON())
                    signal_dict.pop('sell_words')
                    signal_dict.pop('stop_loss_words')
                    signal_dict.pop('buy_zone_words')
                    output = open(os.path.join('./signals/new', filename), "w")
                    output.write(json.dumps(signal_dict))
                    output.close()
                else:
                    filename = "PABS_BAD_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
                    with open("./bad_signals/" + filename, 'w') as text_file:
                        text_file.write(event.raw_text)
            except:
                logging.info("Issue with extracting signal from text")
                filename = "PABS_BAD_TXT_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
                with open("./bad_signals/" + filename, 'w') as text_file:
                    text_file.write(event.raw_text)
        else:
            filename = "PABS_UNMATCHED_" + str(time.strftime("%Y%m%d-%H%M%S")) + ".txt"
            with open("./unmatched_msg/" + filename, 'w') as text_file:
                text_file.write(event.raw_text)

    client.run_until_disconnected()