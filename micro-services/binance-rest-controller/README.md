# Binance REST Controller

Handles all binance REST (apiV3) communications and requests for binance information and order generation

## ENV Requirements

BINANCE_S_APIKEY
BINANCE_S_SECRET
BINANCE_L_APIKEY
BINANCE_L_SECRET


## API

    tracking_number = request.json.get('tracking_number', '')
    market = request.json.get('market', '')
    qty = request.json.get('qty', '')
    price = request.json.get('price', '')
    order_type = request.json.get('order_type', '')



curl -XPOST -H "Content-Type: application/json" -d @./sample_payloads/market_order.json "http://localhost:9009/binance-rest-controller/market_order"

## Input


## Output
