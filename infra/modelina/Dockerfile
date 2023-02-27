FROM modelina:latest

RUN npm install @types/node @asyncapi/parser

RUN mkdir /examples/pydantic && mkdir /examples/pydantic/input && mkdir /examples/pydantic/output

COPY ./src /examples/pydantic

## For testing
COPY ./test /input

RUN cd /examples/pydantic && npm i

WORKDIR /examples/pydantic

CMD npm run start