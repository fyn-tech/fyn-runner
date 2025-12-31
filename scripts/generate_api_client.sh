#!/bin/bash
# Generate API client from Django OpenAPI spec
# Now using JWT authentication - no cookie workarounds needed!

API_DIR=../fyn-api/
RUNNER_DIR=${PWD}
CLIENT_NAME="fyn_api_client"

echo "Generating API client..."

# Activate Python venv and generate OpenAPI spec
source ../venv_fyn/bin/activate
cd ${API_DIR}
python manage.py spectacular --file ${RUNNER_DIR}/fyn_api_client.yaml

# Generate Python client from spec
cd ${RUNNER_DIR}
openapi-generator-cli generate \
  -i fyn_api_client.yaml \
  -g python \
  -o ./${CLIENT_NAME} \
  --additional-properties=packageName=${CLIENT_NAME},packageVersion=1.0.0

pip install --upgrade ${RUNNER_DIR}/fyn_api_client

echo "API client generated successfully!"
