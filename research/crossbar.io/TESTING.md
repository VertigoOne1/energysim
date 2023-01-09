docker run -v 4.nodejs:/app -e CBURL="ws://crossbar:8080/ws" --link=crossbar -e CBREALM="realm1" crossbario/autobahn-js


docker run -v $PWD:/app -e CBURL="ws://crossbar:8080/ws" -e CBREALM="realm1" --link=crossbar --rm -it crossbario/autobahn-python:cpy3 python /app/1.hello-world/client_component_subscribe.py
