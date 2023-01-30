from prometheus_client import Info, Counter, Summary, Gauge, Enum

p_order_sell_requests = Counter('order_sell_requests', 'Number of sell orders that succeeded against exchange')
p_order_sell_failed = Counter('order_sell_failed', 'Number of sell orders that failed against exchange')
p_order_buy_requests = Counter('order_buy_requests', 'Number of buy orders that succeeded against exchange')
p_order_buy_failed = Counter('order_buy_failed', 'Number of buy orders that failed against exchange')
p_ticker_requests = Counter('ticker_requests', 'Number of tickers requested from exchange')
p_ticker_failed = Counter('ticker_failed', 'Number of tickers requests that failed')
p_wallet_requests = Counter('wallet_requests', 'Number of wallet requests from exchange')
p_wallet_failed = Counter('wallet_failed', 'Number of wallet requests that failed')
p_market_requests = Counter('market_requests', 'Number of market requests from exchange')
p_market_failed = Counter('market_failed', 'Number of market requests that failed')

p_events_consumed = Counter('events_consumed', 'Number of events consumed')
p_events_emitted = Counter('events_emitted', 'Number of events emitted')
p_events_valid = Counter('valid_events_consumed', 'Number of events consumed that passed validation')
p_event_validation_errors = Counter('events_failing_validation', 'Number of events consumed that failed validation')
p_payload_validation_errors = Counter('payload_failing_validation', 'Number of events consumed that failed validation')