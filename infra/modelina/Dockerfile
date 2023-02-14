FROM node:lts-alpine

RUN apk add --update npm

RUN mkdir -p /usr/app

WORKDIR /usr/app
COPY ./ /usr/app

# RUN mkdir -p /usr/app/__snapshots__
# RUN mkdir /usr/app/data

# COPY ./ /usr/app

# COPY __snapshots__/* /usr/app/__snapshots__/

RUN npm install /usr/app

VOLUME /usr/app/data

CMD ["npm", "run", "start"]