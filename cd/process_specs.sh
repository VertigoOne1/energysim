#!/bin/bash

SPECS_DIR="/home/marnus/iot/energysim/energysim/data/asyncapi_specs"
PY_MOD_DIR="/home/marnus/iot/energysim/energysim/data/models_python"
TS_MOD_DIR="/home/marnus/iot/energysim/energysim/data/models_typescript"
HTML_DIR="/home/marnus/iot/energysim/energysim/data/asyncapi_html"

rm -rf ${PY_MOD_DIR} && mkdir -p ${PY_MOD_DIR}
rm -rf ${TS_MOD_DIR} && mkdir -p ${TS_MOD_DIR}
rm -rf ${HTML_DIR} && mkdir -p ${HTML_DIR}

cd ${SPECS_DIR}
for FILE in ${SPECS_DIR}/*; do
    echo ${FILE};
    FILENAME=$(basename -- "$FILE")
    EXT="${FILENAME##*.}"
    SPECNAME="${FILENAME%.*}"
    echo "Basename - ${FILENAME}"

    echo "Create HTML - Spec: ${SPECNAME}"
    mkdir -p ${HTML_DIR}/output/${SPECNAME}
    docker run --user $(id -u):$(id -g) -v ${SPECS_DIR}:/input -v ${HTML_DIR}:/output asyncapi:latest asyncapi generate fromTemplate /input/${FILENAME} @asyncapi/html-template --force-write -o /output/${SPECNAME}

    echo "Create Python - Spec: ${SPECNAME}"
    docker run -v ${SPECS_DIR}:/examples/pydantic/input -v ${PY_MOD_DIR}:/examples/pydantic/output infra_pydantic:latest

    # Trim spaces for Python
    for PY_FILE in ${PY_MOD_DIR}/*; do
        sed -i 's/[[:space:]]*$//' "${PY_FILE}"
    done

    echo "Create TypeScript - Spec: ${SPECNAME}"
    docker run --user $(id -u):$(id -g) -v ${SPECS_DIR}:/input -v ${TS_MOD_DIR}:/output asyncapi:latest asyncapi generate models typescript /input/${FILENAME} -o /output/  --tsModelType=class --tsExportType=default --tsEnumType=enum --tsModuleSystem=ESM
done

echo "Done"
