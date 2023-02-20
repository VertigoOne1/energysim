#!/bin/bash

SPECS_DIR=/home/marnus/iot/energysim/energysim/data/asyncapi_specs
PY_MOD_DIR=/home/marnus/iot/energysim/energysim/data/models_python
TS_MOD_DIR=/home/marnus/iot/energysim/energysim/data/models_typescript
HTML_DIR=/home/marnus/iot/energysim/energysim/data/async_api_html

cd ${SPECS_DIR}
for FILE in ${SPECS_DIR}/*; do
    echo ${FILE};
    FILENAME=${FILE##*/}
    echo "Create HTML - ${FILENAME}"
    SPECNAME=${FILE%suffix}
    echo "${SPECNAME}"
    docker run -v ${SPECS_DIR}:/input -v ${HTML_DIR}:/output asyncapi:latest asyncapi generate fromTemplate /input/${FILENAME} @asyncapi/html-template --force-write -o /output/${FILENAME}
done
echo "Done"