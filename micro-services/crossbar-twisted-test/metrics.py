from prometheus_client import Info, Counter, Summary, Gauge, Enum

telegram_messages_received = Counter('telegram_messages_received', 'Messages Received')
telegram_processes_started = Counter('telegram_processes_started', 'Processes Started')
telegram_exceptions_triggered = Counter('telegram_exceptions_triggered', "Exceptions Triggered")