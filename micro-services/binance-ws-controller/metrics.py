from prometheus_client import Info, Counter, Summary, Gauge, Enum

p_events_consumed = Counter('events_consumed', 'Number of events consumed')
p_events_emitted = Counter('events_emitted', 'Number of events emitted')
p_events_valid = Counter('valid_events_consumed', 'Number of events consumed that passed validation')
p_event_validation_errors = Counter('events_failing_validation', 'Number of events consumed that failed validation')
p_payload_validation_errors = Counter('payload_failing_validation', 'Number of events consumed that failed validation')
p_feeds_requested = Counter('feeds_requested', 'Number of feed requests received')

p_ws_feeds_started = Counter('ws_feeds_started', 'Number of feeds started')
p_ws_feeds_stopped = Counter('ws_feeds_stopped', 'Number of feed stopped')
p_active_feeds = Gauge('p_active_feeds', 'Number of active websocket feeds')
p_market_data_events = Counter('market_data_events', 'Number of market data events emitted')
