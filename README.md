# Evidently UI Accelerator

This is an accelerator that can be used to generate a Kubernetes deployment for [Evidently UI](https://www.evidentlyai.com/).

* Install App Accelerator: (see https://docs.vmware.com/en/Tanzu-Application-Platform/1.0/tap/GUID-cert-mgr-contour-fcd-install-cert-mgr.html)
```
tanzu package available list accelerator.apps.tanzu.vmware.com --namespace tap-install
tanzu package install accelerator -p accelerator.apps.tanzu.vmware.com -v 1.0.1 -n tap-install -f resources/app-accelerator-values.yaml
Verify that package is running: tanzu package installed get accelerator -n tap-install
Get the IP address for the App Accelerator API: kubectl get service -n accelerator-system
```

Publish Accelerators:
```
tanzu plugin install --local <path-to-tanzu-cli> all
tanzu acc create evidently-ui --git-repository https://github.com/agapebondservant/evidently-ui-accelerator.git --git-branch main
```

## Contents
1. [Install Evidently via TAP/tanzu cli](#tanzu)
2. [Install Evidently with vanilla Kubernetes](#k8s)

### Install Evidently via TAP/tanzu cli<a name="tanzu"/> (Work in progress)

#### Before you begin (one time setup):
1. Create an environment file `.env` (use `.env-sample` as a template), then run:
```
source .env
```

### Install Evidently via vanilla Kubernetes<a name="k8s"/>

#### Before you begin:
Create an environment file `.env` (use `.env-sample` as a template), then run:
```
source .env
```

1. Deploy the Dashboard:
```
kubectl create ns evidently
kubectl apply -f resources/other/service.yaml -n evidently
watch kubectl get all -n evidently
```

Then access at _http://evidently.<YOUR_FDQN_DOMAIN>_ .

2. To delete the Dashboard:
```
kubectl delete -f resources/other/service.yaml -n evidently
kubectl delete ns evidently
```

## Integrate with TAP

* Deploy the app:
```
source .env
tanzu apps workload create evidently-ui -f resources/workload.yaml --yes
```

* Tail the logs of the main app:
```
tanzu apps workload tail evidently-ui --since 64h
```

* Once deployment succeeds, get the URL for the main app:
```
tanzu apps workload get evidently-ui     #should yield evidently-ui.default.<your-domain>
```

* To delete the app:
```
tanzu apps workload delete evidently-ui --yes
```
