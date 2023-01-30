# PABS signal controller

Takes signals and manages their workflow from new to complete

## API

curl http://localhost:9009/pabs-signal-controller/funding?market=doge/btc

## Input

Signals

## Output

MarketDataRequests
TradeDataRequests

## Default trading settings

# CAREFULLY UNDERSTAND AND REVIEW THESE SETTINGS

```yaml
funding:
  funding_calc_model: dollar_based
  basic_percentage_based: 0.05
  basic_dollar_based: 30.00
validation:
  allow_ask_price_in_entry_zone: False
  maximum_risk_tolerance: 70
  mock: False
targets:
  max_targets_to_process: 3
  distribution:
    t1: [1.0]
    t2: [0.7, 0.3]
    t3: [0.6, 0.3, 0.1]
    t4: [0.5, 0.25, 0.15, 0.1]
  # This allows you to retest updates over and over, it will always reset the signal back until timeout
  never_end_signal_update_processing: False
```