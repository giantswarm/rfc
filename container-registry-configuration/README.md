# Container Registry Configuration

The purpose of this RFC is to specify how we configure Kubernetes clusters for container registries.

## Problem Statement

Docker Hub has [download rate limit](https://docs.docker.com/docker-hub/download-rate-limit/) and it is pretty strict. To use Docker Hub without authentication is not a livable option for us. We started to hit the limit in big CAPI clusters during upgrades.

## Current status

- We use images from different registries. Here is the summary of registry usage of a test MC.
```
explicit docker.io  40
implicit docker.io  2
explicit quay.io    26
explicit k8s.gcr.io 12
```

- We don't configure our Kubernetes clusters for container registries via a central configuration. We mostly rely on public registries and anonymous users. Some applications consume `.dockerConfigJson` from config repo but it is for only `quay.io`.

- We have an infranet page (See `Registry Mirrors`) that states some decisions about which registries we must use. Shortly,
  - We need registry mirrors for high availability.
  - We will not run our own registy.
  - We will use `docker.io` as primary public registry since it has a privilege in docker daemon.
  - We will not use any other public registry (e.g. `quay.io`) as secondary registry because of some security concerns.
  - We will use our own Azure Container Registry as secondary registry.

- In vintage, we configure [containerd for docker registry mirrors](https://github.com/giantswarm/giantnetes-terraform/blob/13700c6d1b1adf8d65fba8b1b37eccf31e1ce4f3/templates/files/conf/containerd-config.toml#L37). 
  
## Possible solutions


### ImagePullSecret

We can set `imagePullSecrets` for all pods with an admission hook for authentication but Kubernetes doesn't have any mechanism like registry mirrors. That is why it is not a viable option.

### FairwindsOps/saffire

There is an open-source project to patch pods in `imagePullErrors` error state: https://github.com/FairwindsOps/saffire

You are able to define alternative source for an image with a Custom Resource.

```
apiVersion: saffire.fairwinds.com/v1alpha1
kind: AlternateImageSource
metadata:
  name: alternateimagesource-sample
spec:
  imageSourceReplacements:
    - equivalentRepositories:
        - quay.io/gianswarm/our-image
        - azurecr.io/giantswarm/our-image
        - docker.io/giantswarm/our-image
```

This mechanism doesn't work for static pods and it doesn't prevent the issue in advance. Also, it has no built-in mechanism for authentication. We can extend it or combine with the image pull secret solution but it sounds too complicated and dirty.


### Containerd Configuration

As we do in vintage clusters, we can configure containerd configuration as below. This seems the best approach.

```
[plugins."io.containerd.grpc.v1.cri".registry]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
endpoint = ["giantswarm.azurecr.io"]

[plugins."io.containerd.grpc.v1.cri".registry.configs]
[plugins."io.containerd.grpc.v1.cri".registry.configs."registry-1.docker.io".auth]
username = "giantswarm-user-account"
password = "my_token_from_docker_hub"
```

## Registry usage

### Which registry should we use? 

The infranet page (See `Registry Mirrors`) states this as a desired configuration:
  - `docker.io` as primary public registry since it has a privilege in docker daemon.
  - Our own Azure Container Registry as secondary registry because of the security concerns

Using only public images without authentication is also on the table. In that case, we will be limited by total of [free account limit](https://docs.docker.com/docker-hub/download-rate-limit/) of Docker Hub (100 pulls per 6 hours per IP address) and [tier limit](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus) of Azure Container Registry (3000 ReadOps per minute for standard). However, anyone can pull images from our registry and spend our limits, which makes us vulnerable. That is why we must use authenticated users.  

### Open Points

## How are we going to configure containerd in cluster app?

We need to provide a configation interface in our `cluster-$provider` apps for the users so that they can provide their credentials. Note that we are the users of our management clusters.

Options:
1. We can ask users to create whole containerd configuration as a secret.
2. We can ask users to provide list of registries and credentials as a secret and render containerd configuration with them.

```
registries:
- name: docker
  endpoint: https://registry-1.docker.io
  username:
  password:
- name: azurecr
  endpoint: giantswarm.azurecr.io
  ...
```

> Note that there can be more than one feature we will support that affects containerd configuration like proxy settings. In this case, we should ensure that the option 1 will not lead conflicts.

### Workload Clusters

- Will we configure workload clusters by default?
- Will we use our credentials for workload clusters by default?

According to the discussion in Kaas Sync, we will configure management clusters and all workload clusters in the management cluster will inherit the configuration from their MCs.

### Configuration Details

- Where will be the source of truth for the container registry configuration? `config` repo or `management-cluster-fleet`?
- How will WCs consume the credentials in their charts? 

### How are going to manage credentials per cluster?

Will we create a user per management cluster?