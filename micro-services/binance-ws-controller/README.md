# Binance WS Controller

Handles all binance WebSocket based communications and requests for trade data and market data from it

## ENV Requirements

BINANCE_S_APIKEY
BINANCE_S_SECRET
BINANCE_L_APIKEY
BINANCE_L_SECRET

## Input

curl -XDELETE "http://localhost:9009/binance-ws-controller/ws_stream?market=SOLUSDT&tracking_number=123&type=trade"

curl -XGET "http://localhost:9009/binance-ws-controller/ws_stream?market=DOGEUSDT&tracking_number=123&type=miniTicker"

### Types of feeds that can be requested

'trade', 'depth', 'depth5', 'depth10', 'aggTrade', 'miniTicker', 'ticker'
'kline_1m', 'kline_5m', 'kline_30m', 'kline_1h', 'kline_15m'

## Output Events

Outputs to trade data topic

pabs-signal-worker         |  'payload': {'trade_data': {'buyer_order_id': 1831780920,
pabs-signal-worker         |                             'event_time': 1640868390353,
pabs-signal-worker         |                             'event_type': 'trade',
pabs-signal-worker         |                             'ignore': True,
pabs-signal-worker         |                             'is_market_maker': True,
pabs-signal-worker         |                             'price': '175.26000000',
pabs-signal-worker         |                             'quantity': '1.37000000',
pabs-signal-worker         |                             'seller_order_id': 1831780940,
pabs-signal-worker         |                             'stream_type': 'solusdt@trade',
pabs-signal-worker         |                             'symbol': 'SOLUSDT',
pabs-signal-worker         |                             'trade_id': 211577952,
pabs-signal-worker         |                             'trade_time': 1640868390352,
pabs-signal-worker         |                             'unicorn_fied': ['binance.com', '0.11.0']}}}