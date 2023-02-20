FROM node:14-alpine

WORKDIR /

RUN npm install @asyncapi/modelina @asyncapi/cli @asyncapi/html-template
RUN npm install ts-node "@types/node@*" "typescript@>=2.7"

WORKDIR /node_modules/.bin
