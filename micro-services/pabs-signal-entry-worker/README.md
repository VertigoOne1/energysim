# PABS signal entry worker

## API

curl -XPOST http://localhost:9009/pabs-signal-worker/reset_signals

curl -XPOST -H "Content-Type: application/json" -d '{"tracking_number":"s18482"}' http://localhost:9009/pabs-signal-entry-worker/terminate_signal

Takes validated signals from the controller and manages their entry workflow from market monitoring to completion of entry process

Poll for a signal to start work on
setup topic for that signal

if the worker restarts, it must read from the db the current signal it is busy with and resume activity from last point,
if the downtime was not significant

request market data at some interval, and start watching for entry point

update and other messages from PABS will go to that topic, which the worker will collect and action
after 14 days, if there is no progress, the signal is closed out

## Input

Validated signals via REST call polling until it has one available
Update messages from PABS

it will need to be controlled via events, where the event would match a tracking number, and the worker 
responsible for that tracking number will then respond appropriately

## Output

MarketDataRequests
TradeDataRequests
SignalUpdates