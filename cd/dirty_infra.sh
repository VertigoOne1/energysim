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

# read -p "Deploy Infra -> Correct? <ENTER>"
sleep 1

echo "--- Active Cluster - ${CLUSTER_CONTEXT}"
echo "--- Active Namespace - ${NAMESPACE}"
echo "Ready"
echo "Deploying namespace object"
kubectl --context ${CLUSTER_CONTEXT} apply --overwrite=true -f infra/namespace-py-event-sys.yaml
sleep 1

## Camunda config file
kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} delete configmap camunda-config
kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} create configmap camunda-config --from-file=../infra/camunda-config/bpm-platform.xml

FILES="infra/secret*"
for f in $FILES
do
  echo "Processing Secrets - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="infra/pvc*"
for f in $FILES
do
  echo "Processing PVC - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done
sleep 1

FILES="infra/svc*"
for f in $FILES
do
  echo "Processing Services - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="infra/cm*"
for f in $FILES
do
  echo "Processing Configmaps - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done

FILES="infra/dep*"
for f in $FILES
do
  echo "Processing Deployments - $f"
  kubectl --context ${CLUSTER_CONTEXT} -n ${NAMESPACE} apply --overwrite=true -f ${f}
done