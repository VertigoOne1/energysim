from prometheus_client import Info, Counter, Summary, Gauge, Enum

p_events_consumed = Counter('events_consumed', 'Number of events consumed')
p_events_emit_success = Counter('events_emitted', 'Number of events emitted')
p_events_emit_failed = Counter('events_emitted_failed', 'Number of events that failed to emit')
p_events_valid = Counter('valid_events_consumed', 'Number of events consumed that passed validation')
p_event_validation_errors = Counter('events_failing_validation', 'Number of events consumed that failed validation')
p_payload_validation_errors = Counter('payload_failing_validation', 'Number of events consumed that failed validation')

## TO BUILD

p_signals_processed = Counter('signals_processed', 'Number of signals processed')
p_signals_success = Counter('signals_success', 'Number of signals resulting in success')
p_signals_success_partial = Counter('signals_success_partial', 'Number of signals resulting in partial success')
p_signals_stoploss = Counter('signals_stoploss', 'Number of signals resulting in stoploss')
p_signals_aged = Counter('signals_aged', 'Number of signals aged out')
p_updates_processed = Counter('updates_processed', 'Number of updates processed')
p_entry_order_success = Counter('entry_order_success', 'Number of binance orders that succeeded')
p_entry_order_failed = Counter('entry_order_failed', 'Number of binance orders that failed')
p_entry_target_order_success = Counter('entry_target_order_success', 'Orders successfully requested')
p_entry_target_order_failed = Counter('entry_target_order_failed', 'Orders unsuccessfully requested')

## Also need to builda routine to calculate the REAL gains vesus reported gains for a target
## then can create averaged gauge of gains, and total gains counter as well
## summation of gains and losses from stoploss calculation to provide current gains gauge

p_update_last_seen = Info('update_last_seen','The last update emitted for processing')
p_signal_last_seen = Info('signal_last_emitted','The last signal emitted for processing')
p_signals_active_count = Gauge('signals_active_count', 'Number of active signals')
p_targets_active_count = Gauge('targets_active_count', 'Number of signals in target state')
p_entry_active_count = Gauge('entry_active_count', 'Number of signals in waiting entry state')
p_funding_needed_count = Gauge('funding_needed_count', 'Number of signals requiring funding')

signal_info = Summary('signal_info', 'HTTP Failures', ['tracking_number', 'market', 'status'])
signal_info.labels(tracking_number='s123', market='DOGEBTC', status='ACTIVE').observe(1)