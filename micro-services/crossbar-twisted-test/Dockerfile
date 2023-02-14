FROM python:3.10-alpine

WORKDIR /

# RUN apk update && apk add gcc \
#                           build-base \
#                           librdkafka-dev \
#                           mariadb-dev

# RUN apk update && apk add gcc \
#                           build-base \

# COPY modules/camunda /modules/camunda

COPY requirements.txt requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt

# COPY modules/ /modules/

ENV BROKER_URL=localhost:9092
ENV DEBUG_LEVEL=DEBUG
ENV API_CONTROLLER_PORT=8088

VOLUME /data

COPY . .

CMD [ "python", "./app.py" ]