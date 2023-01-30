# msg from telegram

Ingests PABS chat messages into raw message events and emits them

## API's

### Requeue a message from db based on ID

The assumption being the message failed processing, you fixed the code and want to requeue the message

curl -XPOST -H "Content-Type: application/json" -d '{"id":13}' http://localhost:9009/pabs-msg-from-telegram/requeue