---
creation_date: 2023-03-01
issues:
- https://github.com/giantswarm/giantswarm/issues/24237
last_review_date: 2024-02-26
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: obsolete
summary: Since Docker Hub has an image download rate limit which can lead to unhealthy clusters, configure containerd to use our Azure Container Registry as mirror and keep Docker Hub as primary. Also make this the default on WCs. Use per-MC authenticated Giant Swarm account for our registries to avoid public pulls using up all our limits. See RFC for details on secret handling and cluster chart values to configure this.
---

# Container registry configuration

The purpose of this RFC is to specify how we configure Kubernetes clusters for container registries.

## Problem Statement

Docker Hub has [download rate limit](https://docs.docker.com/docker-hub/download-rate-limit/) and it is pretty strict. To use Docker Hub without authentication is not a livable option for us. We started to hit the limit in big CAPI clusters during upgrades.

## Current status

- We use images from different registries. Here is the summary of registry usage of a test MC.

  ```text
  explicit docker.io  40
  implicit docker.io  2
  explicit quay.io    26
  explicit k8s.gcr.io 12
  ```

- We don't configure our Kubernetes clusters for container registries via a central configuration. We mostly rely on public registries and anonymous users. Some applications consume `.dockerConfigJson` from config repo but it is for only `quay.io`.

- We have an intranet page (See `Registry Mirrors`) that states some decisions about which registries we must use. Shortly,
  - We need registry mirrors for high availability.
  - We will not run our own registy.
  - We will use `docker.io` as primary public registry since it has a privilege in docker daemon.
  - We will not use any other public registry (e.g. `quay.io`) as secondary registry because of some security concerns.
  - We will use our own Azure Container Registry as secondary registry.

- In vintage, we configure [containerd for docker registry mirrors](https://github.com/giantswarm/giantnetes-terraform/blob/13700c6d1b1adf8d65fba8b1b37eccf31e1ce4f3/templates/files/conf/containerd-config.toml#L37).

## Design proposals

### 1. How to solve ImagePullErrors

#### 1.a ImagePullSecret

We can set `imagePullSecrets` for all pods with an admission hook for authentication but Kubernetes doesn't have any mechanism like registry mirrors. That is why it is not a viable option.

#### 1.b FairwindsOps/saffire

There is an open-source project to patch pods in `imagePullErrors` error state: https://github.com/FairwindsOps/saffire

You are able to define alternative source for an image with a Custom Resource.

```yaml
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

#### 1.c containerd configuration

As we do in vintage clusters, we can configure containerd configuration as below. This seems the best approach.

```toml
[plugins."io.containerd.grpc.v1.cri".registry]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
endpoint = ["giantswarm.azurecr.io"]

[plugins."io.containerd.grpc.v1.cri".registry.configs]
[plugins."io.containerd.grpc.v1.cri".registry.configs."registry-1.docker.io".auth]
username = "giantswarm-user-account"
password = "my_token_from_docker_hub"
```

#### Decision

`1.c` is selected.
We will use containerd configuration.

### 2. Authentication

#### 2.a Using unauthenticated accounts

Using only public images without authentication is an option to avoid complexity of securing credentials. However, registry providers have pull/rate limits per account. We will be limited by total of [free account limit](https://docs.docker.com/docker-hub/download-rate-limit/) of Docker Hub (100 pulls per 6 hours per IP address) and [tier limit](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus) of Azure Container Registry (3000 ReadOps per minute for standard). Anyone can pull images from our registry and spend our limits, which makes us vulnerable.

#### 2.b Using authenticated accounts

We can pass credentials to `containerd` configuration to be not limited by registry provider limits.

#### Decision

`2.b` is selected.
We will use authenticated accounts.

### 3. Registries

The intranet page (See `Registry Mirrors`) states this as a desired configuration:

- `docker.io` as primary public registry since it has a privilege in docker daemon.
- Our own Azure Container Registry as secondary registry because of the security concerns

Since we use `containerd`, docker has not a privilege anymore but there is no need to change this order at the moment. We will follow this configuration for CAPI clusters too.

Also, users must be able to customize the configuration for their workload clusters. Additional registries and additional mirrors for existing registries must be supported.

### 4. Accounts

- 4.a Giant Swarm Account + Single account
- 4.b Giant Swarm Account + Per MC including its WCs
- 4.c Giant Swarm Account + Per WC
- 4.d Customer Accounts

#### Decision

`4.b` is selected: Giant Swarm Account + Per MC including its WCs.

Since it is a part of the platform itself, we are going to use Giant Swarm accounts in containerd configuration.
As we do for other operators, we will follow "per MC" approach here to.

### 5. Default configuration for WCs

- 5.a: Configuring WCs by default
- 5.b: Not configuring WCs by default

#### Decision

`5.a` is selected: configuring WCs by default.

### 6. How to propogate credentials and where to put them

#### 6.a cluster-apps-operator

We can propogate credentials from MC to WC by using `cluster-apps-operator`. It can create a secret per WC with the credentials.

#### 6.b Customer's Git Repository

We can put the secret into customers' git repositories and use GitOps templates to use the same credentials for all WCs.

#### 6.c Management Cluster Fleet

We can put the secret into our `management-clusters-fleet` repo and refer that secret in `extraConfigs` in cluster apps. We can use GitOps templates to inject this configuration in all cluster apps.

#### 6.d Catalog configuration

We can use catalog configurations (See `<mc-name>/appcatalog` folder in `installations` repo) to provide a MC specific configuration to all charts in the cluster.

#### Decision

`6.c` is selected: secrets in `management-clusters-fleet` repo.

- Regarding 6.a, we don't want to add another responsility to `cluster-apps-operator`.
- Regarding 6.b, we want to manage the credentials in our side and to have a full control over them.
- Regarding 6.d, people think catalog configurations are hard to track since there is no references in app CRs.

### 7. Configuration interface

How will be the configuration interface in `cluster-$provider` apps?

#### 7.a Full containerd configuration

We can implement a full transitive configuration interface so that users can provide a full containerd configuration, including registy credentials.

#### 7.b Only registry configuration in a structured way

We can define a configuration interface like below and render containerd configuration in `cluster-$provider` app chart.

```yaml
connectivity:
 containerRegistries:
   docker.io:
    - endpoint: "registry-1.docker.io"
       credentials:
         username: "my_user_name"
         password: "my_password"
   - endpoint: "my-mirror-registry.mydomain.io"
```

#### Decision

`7.b` is selected: only certain fields are made configurable.

7.a seems risky. Also, there can be other configurations (e.g. proxy) that touch containerd configuration too. 7.a can be error prone.
