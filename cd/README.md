## Solution Delivery

### Install monitoring

```bash
helm repo add prometheus-community https://prometheus-community.dockerhub.io/helm-charts
helm repo update
helm install prom prometheus-community/prometheus --kube-context atlantis -n monitoring --create-namespace -f ./helm-charts/kube-prometheus/values.yaml
```


After deployment of mysql, you need to connect as the root user and

```sql
GRANT ALL PRIVILEGES ON *.* TO 'pyeventsys'@'%';
FLUSH PRIVELEGES;
```

use container shell

Delivery objects for kubernetes neccessary to allow the solution to function

then run

```bash
./dirty_infra.sh -c {context} -n py-event-sys
```

Check cluster that everything goes green

then run

```bash
./dirty_micro.sh -c {context} -n py-event-sys
```




## Run cronjob manually

### Internal cert checker

kubectl -n devops-certificate-monitoring create job --from=cronjob/cert-checker-internal-cronjob internal-test-1

### External cert checker

kubectl -n devops-certificate-monitoring create job --from=cronjob/cert-checker-external-cronjob external-test-1

ip8z84zeMJpu##

## Infra images to fix into harbor
envoyproxy/envoy:v1.9.1
confluentinc/cp-kafka:latest
confluentinc/cp-zookeeper:latest
mysql:latest
camunda/camunda-bpm-platform:latest

docker pull envoyproxy/envoy:v1.9.1
docker pull confluentinc/cp-kafka:latest
docker pull confluentinc/cp-zookeeper:latest
docker pull mysql:latest
docker pull camunda/camunda-bpm-platform:latest

docker tag envoyproxy/envoy:v1.9.1 harbor.marnus.com:443/library/py-event-sys-envoy:current
docker tag confluentinc/cp-kafka:latest harbor.marnus.com:443/library/py-event-sys-kafka:current
docker tag confluentinc/cp-zookeeper:latest harbor.marnus.com:443/library/py-event-sys-zookeeper:current
docker tag mysql:latest harbor.marnus.com:443/library/py-event-sys-mysql:current
docker tag camunda/camunda-bpm-platform:latest harbor.marnus.com:443/library/py-event-sys-camunda:current

docker push harbor.marnus.com:443/library/py-event-sys-envoy:current
docker push harbor.marnus.com:443/library/py-event-sys-kafka:current
docker push harbor.marnus.com:443/library/py-event-sys-zookeeper:current
docker push harbor.marnus.com:443/library/py-event-sys-mysql:current
docker push harbor.marnus.com:443/library/py-event-sys-camunda:current