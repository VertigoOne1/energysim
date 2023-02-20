FROM node:16-alpine

WORKDIR /

RUN npm install @asyncapi/modelina @asyncapi/cli
RUN npm install ts-node "@types/node@*" "typescript@>=2.7"

COPY /app /app