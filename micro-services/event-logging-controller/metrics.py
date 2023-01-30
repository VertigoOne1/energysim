from prometheus_client import Info, Counter, Summary, Gauge, Enum

p_exceptions = Counter('exceptions','Counts the number of exceptions')
p_logging_events_consumed = Counter('logging_events_consumed', 'Number of logging_events consumed')
p_logging_events_stored = Counter('logging_events_stored', 'Logging events written to DB')