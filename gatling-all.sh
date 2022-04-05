#!/usr/bin/env bash
docker container run --detach --rm \
  -v ${PWD}/gatling/results:/opt/gatling/results \
  -v ${PWD}/gatling:/opt/gatling/user-files \
  -v ${PWD}/gatling/target:/opt/gatling/target \
  -e CLUSTER_IP=`tools/getip.sh kubectl istio-system svc/istio-ingressgateway` \
  -e USERS=${1} \
  -e PAUSE=${2} \
  -e SIM_NAME=ReadAllSim \
  --label gatling \
  -s proj756.ReadAllSim