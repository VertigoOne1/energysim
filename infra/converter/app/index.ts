import { TypeScriptGenerator } from '@asyncapi/modelina';
import { ParseOutput, Parser } from '@asyncapi/parser';
import { PythonGenerator, PYTHON_PYDANTIC_PRESET } from '@asyncapi/modelina';

const pygenerator = new PythonGenerator({
  presets: [PYTHON_PYDANTIC_PRESET]
});

const tsgenerator = new TypeScriptGenerator();

const AsyncAPIDocument = `
asyncapi: 2.6.0
info:
  title: 'Signup Service'
  version: 1.0.0
  description: 'This service is in charge of processing user signups'
channels:
  user/signedup:
    subscribe:
      message:
        description: An event describing that a user just signed up.
        $ref: '#/components/messages/UserSignedUp'
  user/signingup:
    publish:
      message:
        description: An event describing that a user is signing up.
        $ref: '#/components/messages/UserSignUp'
servers:
  rabbitmq-dev:
    url: localhost:5672
    description: Local RabbitMQ
    protocol: amqp
    protocolVersion: "0.9.1"
components:
  messages:
    UserSignedUp:
      name: exampleMessage
      title: Example message
      payload:
        $id: UserSignedUp
        type: object
        additionalProperties: false
        properties:
          email:
            type: string
            format: email
            description: Email of the user
    UserSignUp:
      name: exampleMessage 2
      title: Example message 2
      payload:
        $id: UserSignUp
        type: object
        additionalProperties: false
        properties:
          displayName:
            type: string
            description: Name of the user
          email:
            type: string
            format: email
            description: Email of the user
          password:
            type: string
            format: email
            description: Password for creation
`

// const AsyncAPIDocument = {
//   asyncapi: '2.2.0',
//   info: {
//     title: 'example',
//     version: '0.1.0'
//   },
//   channels: {
//     '/receiveEmailAddress': {
//       subscribe: {
//         message: {
//           payload: {
//             $schema: 'http://json-schema.org/draft-07/schema#',
//             $id: 'emailAddress',
//             type: 'object',
//             additionalProperties: false,
//             properties: {
//               email: {
//                 type: 'string',
//                 format: 'email'
//               }
//             }
//           }
//         }
//       }
//     }
//   }
// };


export async function generatets(): Promise<void> {
  const parser = new Parser();
  const { document } = await parser.parse(AsyncAPIDocument);
  parser.parse
  const modelsts = await tsgenerator.generate(document);
  for (const modelts of modelsts) {
    console.log("AsyncAPI -> Typescript");
    console.log("-");
    console.log(modelts.result);
    console.log("-");
  }
}

export async function generatepy(): Promise<void> {
  const parser = new Parser();
  const { document } = await parser.parse(AsyncAPIDocument);
  const modelspy = await pygenerator.generate(document);
  for (const modelpy of modelspy) {
    console.log("AsyncAPI -> Python - Pydantic");
    console.log("-");
    console.log(modelpy.result);
    console.log("-");
  }
}

if (require.main === module) {
  generatets();
  generatepy();

}
