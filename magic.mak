docker_images: templates
	make -f k8s.mak cri

deploy_all: templates create_cluster provision urls

templates:
	make -f k8s.mak templates

create_cluster:
	make -f eks.mak start
	kubectl config use-context aws756
	kubectl create ns c756ns
	kubectl config set-context aws756 --namespace=c756ns

provision:
	make -f k8s.mak provision
	make -f k8s.mak loader

urls:
	kubectl -n istio-system get service istio-ingressgateway | cut -c -140
	make -f k8s.mak kiali-url
	make -f k8s.mak grafana-url

teardown:
# Delete everything on cluster and then delete the cluster itself
	make -f k8s.mak scratch
	make -f eks.mak stop
	make -f k8s.mak dynamodb-clean
