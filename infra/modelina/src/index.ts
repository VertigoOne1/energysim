import { PythonGenerator, PYTHON_PYDANTIC_PRESET } from '../../src';
import { ParseOutput, Parser } from '@asyncapi/parser';
import * as fs from 'fs';
import { join } from 'path';

const source_path: string = '/input/';
const dest_path: string = '/output/';

async function scanDir(path: string) {
  const dir = await fs.promises.opendir(path);
  for await (const dirent of dir) {
    const file = fs.readFileSync(path + dirent.name, 'utf-8');
    // console.log("Spec: " + dirent.name);
    // console.log(file)
    generate(file, dirent.name);
  }
};

function syncWriteFile(filename: string, data: any) {
  const prepend1: string = "from pydantic import *";
  const prepend2: string = "from typing import *";

  const output = prepend1 + "\n" + prepend2 + "\n\n" + data;
  fs.writeFileSync(join(__dirname, filename), output, { flag: 'w' });
}

const generator = new PythonGenerator({
  presets: [PYTHON_PYDANTIC_PRESET]
});

export async function generate(input: string, name: string): Promise<void> {
  const parser = new Parser();
  // console.log("Parsing...")
  const { document } = await parser.parse(input)
  // console.log("Generating...")
  const models = await generator.generate(document)
  for (const model of models) {
    syncWriteFile(dest_path + model.modelName + '.py', model.result);
    // console.log(model.modelName);
    // console.log(model.result);
  }
};

if (require.main === module) {
  scanDir(source_path).catch(console.error)
}
