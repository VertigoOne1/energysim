#!/bin/bash

## Very quick and dirty solution deployer

usage() { echo "Usage: $0 [-c <cluster>] [-n <namespace>]" 1>&2; exit 1; }
no_args="true"
while getopts "c:n:h" flag
do
    case "${flag}" in
        c) CLUSTER_CONTEXT=${OPTARG};;
        n) NAMESPACE=${OPTARG};;
        h | *) usage;;
    esac
    no_args="false"
done
[[ "$no_args" == "true" ]] && { usage; exit 1; }
echo "Cluster: ${CLUSTER_CONTEXT}"
echo "Namespace: ${NAMESPACE}"

## Which config file to use
CONFIG_FILE=config_prod.yml

# read -p "Deploy Micro Services -> Correct? <ENTER>"
sleep 1

echo "--- Active Cluster - ${CLUSTER_CONTEXT}"
echo "--- Active Namespace - ${NAMESPACE}"
echo "Ready"
echo "Deploying namespace object"
kubectl --context ${CLUSTER_CONTEXT} apply --overwrite=true -f infra/namespace-py-event-sys.yaml
sleep 1

echo "Deploying configmaps"
services=(event-logging-controller event-ping event-pong pabs-msg-from-file pabs-msg-from-telegram pabs-msg-to-signal pabs-msg-to-other pabs-msg-to-update pabs-signal-controller pabs-signal-entry-worker binance-rest-controller binance-ws-controller pabs-signal-update-worker telegram-controller)

for s in "${services[@]}"
do
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete configmap ${s}-config
  sleep 0.1
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create configmap ${s}-config --from-file=../micro-services/${s}/${CONFIG_FILE} --from-file=../micro-services/${s}/config.yml
done

echo "Creating config file name secret for all containers"
## Might fail
kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete secret pabs-config-file

kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create secret generic pabs-config-file \
  --from-literal=CONFIG_FILE=${CONFIG_FILE}

kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete secret telegram-config-file

kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create secret generic telegram-config-file \
  --from-literal=CONFIG_FILE=${CONFIG_FILE}

echo "Creating binance secrets"
## Might fail
kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete secret binance-secrets
kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete secret telegram-secrets

kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create secret generic binance-secrets \
  --from-literal=BINANCE_S_SECRET=${BINANCE_S_SECRET} \
  --from-literal=BINANCE_L_SECRET=${BINANCE_L_SECRET} \
  --from-literal=BINANCE_SANDBOX_ACTIVE=${BINANCE_SANDBOX_ACTIVE} \
  --from-literal=BINANCE_L_APIKEY=${BINANCE_L_APIKEY} \
  --from-literal=BINANCE_S_APIKEY=${BINANCE_S_APIKEY} \
  --from-literal=BINANCE_MOCK_ACTIVE=${BINANCE_MOCK_ACTIVE}

kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create secret generic telegram-secrets \
  --from-literal=TELEGRAM_API_ID=${TELEGRAM_API_ID} \
  --from-literal=TELEGRAM_API_HASH=${TELEGRAM_API_HASH} \
  --from-literal=TELEGRAM_GEN1_SESSION=${TELEGRAM_GEN1_SESSION} \
  --from-literal=TELEGRAM_PABS_SESSION=${TELEGRAM_PABS_SESSION}

FILES="micro-services/secret*"
for f in $FILES
do
  echo "Processing Secrets - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="micro-services/pvc*"
for f in $FILES
do
  echo "Processing PVC - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="micro-services/svc*"
for f in $FILES
do
  echo "Processing Services - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="micro-services/cm*"
for f in $FILES
do
  echo "Processing Configmaps - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="micro-services/dep*"
for f in $FILES
do
  echo "Processing Deployments - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} rollout restart deployment/${f:19:-5}
done