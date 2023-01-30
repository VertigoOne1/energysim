from prometheus_client import Info, Counter, Summary, Gauge, Enum

p_events_consumed = Counter('events_consumed', 'Number of events consumed')
p_events_emitted = Counter('events_emitted', 'Number of events emitted')
p_events_valid = Counter('valid_events_consumed', 'Number of events consumed that passed validation')
p_event_validation_errors = Counter('events_failing_validation', 'Number of events consumed that failed validation')
p_payload_validation_errors = Counter('payload_failing_validation', 'Number of events consumed that failed validation')