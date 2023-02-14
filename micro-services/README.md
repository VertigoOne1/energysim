# Current development targets

## Sample crypto action signal

```text
New signal: #QNT

QNT/BTC: ideas, news. V: 6.93 BTC
Avg: buy -1.03% from top, profit +8.07%. Risk: 18%

#QNT
Buy it price  =0.002970—0.003095
SL  0.002724
Sell: 0.003293


Signal: /s18176, or view all /signals
```

Review more samples under pabs-msg-from-file/data/msgs

## Environment Variables

Intended to control the kubernetes side of it to split dev/test/prod. The following can be set.
Some settings are not ENV because i have not needed to be able to split them out.

```bash
BROKER_URL=pabs-kafka:9092
DEBUG_LEVEL=DEBUG
API_CONTROLLER_PORT=8080
KAFKA_DEBUG_LEVEL=INFO
TOPIC_PREFIX=test_
```

TOPIC_PREFIX is likely the most useful as it will prefix any topic consumption or production to a subname, thus you can do prod_binance, and prod_logging on the same kafka cluster

the last two controls if the requests will go to binance production, sandbox, or be completely mocked with sample responses. These are incomplete, but it will very safely prevent throwing money into a hole

TRACE level is available for DEBUG_LEVEL, but not for KAFKA_DEBUG_LEVEL

Note that with the introduction of BPM, a lot of the Events are being wired out as they are converted to messages or process maps

## To do

### High priority

1. Build some interogation reports, active streams, signal last status...
2. Grafana dashboards for every service

### Nice to have

Black listing - controller checks signal against a list of banned coins

# Service Status

Some of this is now updated because i moved to Camunda, so not all the events are used anymore as they are better done using orchestration

## event-logging-controller

Fully functional

### Function

Fully functional

### Status

This service simply consumes the kafka topic where all the microservices are sending their logs. Since zipkin was a bit of an overkill, i simply added a log handler to send everything to a topic for analysis as required.

### Input

topic : logging

### Output

stdout, but the code for DB dumping is there, but i'm looking to elastic search, etc etc

## pabs-msg-from-file

### Function

directory under data/msgs can be used to inject files for manually testing eventing and classification by the other microservices

### Status

Fully functional

### Input

Text file (PABS layout), check layout under data

### Output

event with the message from the text file as PabsRawMessageEvent

## pabs-msg-from-telegram

### Function
Consumes telegram channel(s) for trading messages from PABS
Requires API key configured within environment

### Status
Fully functional

### Input

PABS telegram channel (but it will obviously take any channel)

### Output

event with the telegram message body as raw_message as PabsRawMessageEvent

## pabs-msg-to-signal

### Function
constructs an event with well defined signal dict to be actioned by trader algo

### Status
Fully functional

### Input

PabsRawMessageEvent

### Output

PabsSignalEvent

## pabs-signal-controller

### Function
Processes new signal events, checks their validity, funds them, and makes farms them to workers

### Status
Fully Functional, Signal updates are in testing

### Input

PabsSignalEvent
PabsUpdateEvent

### Output

PabsSignalEvent
PabsSignalUpdateEvent
PabsUpdateUpdateEvent

## pabs-signal-entry-worker

### Function
Processes signals that are to be funded, validated and ready for market information, then watches binance websocket events for pricing that matches requirements

### Status
Fully Functional

### Input

PabsSignalEvent
MarketDataEvent

### Output

PabsSignalEvent
PabsSignalUpdateEvent

## pabs-signal-update-worker

### Function
Processes signal updates, ensures sales are executed with binance, and manages the rest of that process

### Status
Fully Functional

### Input

PabsSignalEvent
MarketDataEvent

### Output

PabsSignalEvent
PabsSignalUpdateEvent

## pabs-msg-to-update

### Function
Takes PABS raw messages and turn them into update message dict

### Status
In Testing, handling of the various states

## Input

PabsRawMessageEvent

## Output

PabsUpdateEvent

## pabs-msg-to-other

Not implemented yet, handing other administrative messages from the PABS channel, like signal expiry or cancellation

## binance-ws-controller

### Function
Processes events for market data and sets up streams from binance as websockets into event streams for internal consumption

### Status
Fully Functional

### Input

MarketDataRequestEvent

### Output

MarketDataEvent

## binance-rest-controller

### Function
Processes events for binance API based interaction data and sets up and responds for it for signals and other requirements

### Status
In testing, currently mocking, but just need to be uncommented for full testing with real money

### Input

MarketDataRequestEvent
BinanceTradeInstruction

### Output

BinanceTradeResult

## event-ping

### Function

Implements a test routine to ensure the event bus is functioning properly by transmitting ping events to topic

### Status

Fully functional

## event-pong

### Function

Implements a test routine to ensure the event bus is functioning properly by consuming ping events from a topic

### Status

Fully functional

## Outstanding services

- Wallet metrics, trade, logging, grafana dashboards, auditing
- Clear before/after picture generation for sucess evaluation
- Smart wallet tracker dashboard
- push pull of metrics for watched assets to identify buy/sell ops using other sources (not PABS related)