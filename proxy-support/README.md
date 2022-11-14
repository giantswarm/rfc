---
title: Management- and Workload-clusters behind a proxy
authors:
- "@bavarianbidi"
reviewers:
- TBD
approvers:
- TBD
editor: TBD
creation-date: 2022-22-10
last-updated: 
status: provisional
see-also:
replaces: 
superseded-by:
---

# Management- and Workload-clusters behind a proxy

## Table of Contents

<!-- toc -->
- [Glossary](#glossary)
- [Summary](#summary)
- [Motivation](#motivation)
- [Affected Components](#affected-components)
  - [<code>containerd</code>](#containerd)
  - [workload on top of Kubernetes](#workload-on-top-of-kubernetes)
    - [special workload](#special-workload)
      - [<code>cert-manager</code>](#cert-manager)
      - [<code>chart-operator</code>](#chart-operator)
- [<code>no_proxy</code>/<code>NO_PROXY</code>](#no_proxyno_proxy)
- [Implementation](#implementation)
  - [Management Cluster](#management-cluster)
    - [during the initial bootstrap](#during-the-initial-bootstrap)
    - [after all controllers/operators are in place](#after-all-controllersoperators-are-in-place)
  - [Workload Clusters](#workload-clusters)
    - [<a href="(https://github.com/giantswarm/cluster-apps-operator)"><code>cluster-apps-operator</code></a>](#cluster-apps-operator)
- [To be discussed](#to-be-discussed)
- [Current known limitations and issues:](#current-known-limitations-and-issues)
- [Tasks, Stories and PRs](#tasks-stories-and-prs)
  - [Tasks](#tasks)
  - [PRs](#prs)
<!-- /toc -->

## Glossary

- Management Cluster (`MC`): A cluster which hosts all ClusterAPI controllers and extend this with Giant Swarm specific features like GitOps tooling and an observability stack.
- Workload Cluster (`WC`): A cluster created by a ClusterAPI controller, which is meant to be used by end-users.
- Installation: An installation defines the combination of a `MC` with all the provisioned `WCs` from there.
- App Platform: Refers to a set of features and concepts that allow to browse, install and manage the configurations of apps from the management cluster.
- Proxy configuration: In most cases a combination of valid `http_proxy`,`https_proxy` and `no_proxy` environment variables.

## Summary

Goal of this proposal is to collect all requirements and information needed to create an installation from scratch behind a proxy server.

## Motivation

Due some security related policies, some customers are enforced to use a corporate proxy server when accessing external resources. Beside some application specific API endpoints this also affects accessing our used:

- container registries (e.g. `quay.io`, `docker.io`)
- GitOps workflow (e.g. accessing `github.com`)

## Affected Components

### `containerd`

To make `containerd` use of a proxy configuration for pulling container images, it's required to create a `systemd` drop-in and place it under `/etc/systemd/system/containerd.service.d/http-proxy.conf`.

```
[Service]
Environment="HTTP_PROXY={{ .HttpProxy }}"
Environment="http_proxy={{ .HttpProxy }}"
Environment="HTTPS_PROXY={{ .HttpsProxy }}"
Environment="https_proxy={{ .HttpsProxy }}"
Environment="NO_PROXY={{ .NoProxy}}"
Environment="no_proxy={{ .NoProxy }}"
```

### workload on top of Kubernetes

Every pod within a Kubernetes cluster needs a valid proxy configuration if the pod needs to access external systems.

On a `MC` there are a lot of components which needs access to external systems:

- `Flux` needs access to `github.com`
- The entire monitoring and alerting stack needs access to `opsgenie`, `grafana`, ...
- App platform components need access to an OCI artifact system (e.g. `github.com`, `azure`)

As we already use `kyverno` in our `MC`, we can use the [`kyverno-policies-connectivity`] chart to inject the proxy configuration into all pods.

> Please note: 
> - due multiple valid reasons, `kyverno` doesn't mutate objects in `namespace/kube-system` per default.
> - static pods are managed by the `kubelet`. For these pods it's not possible to use `kyverno` for mutation. Therefore it's required to inject the proxy configuration during the machine creation phase (could be achieved in `CAPI` based clusters via `kubeadm`)

#### special workload

There are some components, which are part of the default set on top of a cluster. These components can't get configured via `kyverno` as they are either in `namespace/kube-system` (for `cert-manager`) or must exist before we apply applications via the app platform (for `chart-operator`).

##### `cert-manager`

As `cert-manager` is needed in every cluster (`MC` and `WC`) and it's running in `namespace/kube-system`. `cert-manager` interact with external `ACME` services (`lets encrypt` at the moment).
The proxy configuration must be explicitly defined in the `pod.spec`.

##### `chart-operator`

`chart-operator` is getting deployed in every `WC` by `cluster-apps-operator` and is responsible for applying charts in the workload cluster.
The proxy configuration must be explicitly defined in the `pod.spec`. 

## `no_proxy`/`NO_PROXY`

Due possible security policies, customers wants components using a proxy server for external systems. But there might be also internal systems where no proxy server should be used. For that it's possible to define a comma separated list of domain names, FQDNs, network addresses and network ranges.

As within a Kubernetes cluster there are also some targets where no communication via the proxy is expected (e.g.: accessing Kubernetes services within the cluster, directly accessing pods via their IP address - primarily used by `prometheus` for metrics scraping).

For that, the values of `no_proxy` are separated into two logical parts:

- endpoints which are installation wide like a customer internal container registry or a customer internal network range.
- endpoints which are cluster specific like the `podCIDR`/`serviceCIDR` or the cluster internal base domain (e.g. `cluster.local`)

> Note: the interpretation of the `no_proxy` variable is very language/tool specific and not every language supports e.g. network ranges.
> a very details blog post was written by GitLab about [proxy variables].

## Implementation

### Management Cluster

#### during the initial bootstrap

During the initial bootstrap phase of the `MC`, there isn't the entire App Platform running. For that reason it's required to define the proxy configuration multiple times.

#### after all controllers/operators are in place

After the initial bootstrap is done and all GiantSwarm specific controllers and operators are in place to treat the `MC` as a `WC`, [`cluster-apps-operator`] will take over the handling of the installation specific proxy configuration.

### Workload Clusters

The current implemented workflow can be visualized like this:

![](data/workload_cluster_creation.svg)

#### [`cluster-apps-operator`]

As the proxy configuration is something which exists (for now) on a installation base and must be injected on a WC base (to make cluster-lifecycle work), in [PR #290] [`cluster-apps-operator`] got extended to propagate global proxy configuration into workload cluster specific resources.

[`cluster-apps-operator`] can then be configured to accept following configuration as additional input (added as `configmap-values.yaml.patch` and `secret-values.yaml.patch` in the [`config`]-repo):

```yaml
proxy:
  noProxy: "172.16.0.0/16,internal.corpdomain.net,example.com"
  http: "http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
  https: "http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
```

As [`cluster-apps-operator`] already creates a `configmap` for each WC called `<clusterName>-cluster-values`, with the extended proxy implementation, the `cluster` section of the `configmap` now contains a `proxy` sub section:

```yaml
calico:
  CIDR: 100.96.0.0/11
kubernetes:
  API:
    clusterIPRange: 10.96.0.0/12
  DNS:
    IP: 10.96.0.10
proxy:
  noProxy: cluster.local,100.64.0.0/13,100.96.0.0/11,178.170.32.59,172.16.0.0/16,internal.corpdomain.net,example.com,svc,127.0.0.1,localhost
```

[`cluster-apps-operator`] also creates a `secret` which contains some infrastructure specific values ([for `openstack` and `vcd`](https://github.com/giantswarm/cluster-apps-operator/blob/master/service/controller/resource/clustersecret/desired.go#L42-L65)).
The `secret` for each WC is called `<clusterName>-cluster-values`.
With the extended proxy implementation, the secret now contains a new `cluster` section with a `proxy` sub section:

```yaml
cluster:
  proxy:
    httpProxy: http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128
    httpsProxy: http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128
```

This `secret` and `configmap` can now be used to pass these information into `Apps` which get applied into a WC.
As `cert-manager` needs this data, the manifest should now look like:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
[...]
spec:
  catalog: default-test
  config:
    configMap:
      name: mycluster-cluster-values
      namespace: org-giantswarm
    secret:
      name: mycluster-cluster-values
      namespace: org-giantswarm
[...]
```

As we have these information on a cluster-base, we are now able to create a new `secret`, called `<clusterName>-systemd-proxy` which is a rendered version of [this](#containerd) systemd drop-in. In our example, the `secret` now looks like

```yaml
[Service]
Environment="HTTP_PROXY=http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
Environment="http_proxy=http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
Environment="HTTPS_PROXY=http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
Environment="https_proxy=http://myProxyUser:mySuperSecretPassword@192.168.52.220:3128"
Environment="NO_PROXY=172.16.0.0/16,internal.corpdomain.net,example.com"
Environment="no_proxy=172.16.0.0/16,internal.corpdomain.net,example.com"
```

This secret can now be referenced in a `kubeadmconfig`, e.g.:

```yaml
files:
  - path: /etc/systemd/system/containerd.service.d/http-proxy.conf
    permissions: "0600"
    contentFrom:
      secret:
        name: <clusterName>-systemd-proxy
        key: containerdProxy   
```

By doing this, `ClusterAPI` is waiting for the `secret` to get created. Once the `secret` got created, it will be used by creating the machines (and injecting this data via `cloud-init` or `ignition`).

As `cluster-apps-operator` takes care of creating `deployment/chart-operator` in the WC with the values from `(secret|configmap)/<clusterName>-cluster-values` as input, `chart-operator` in every WC automatically get a valid proxy configuration.

## To be discussed

- Customers are able to see the proxy configuration (especially the secret part) within a `WC`. Is this a security issue?
- Should the [`cluster-apps-operator`] known installation wide proxy configuration propagated into WCs for [`kyverno-policies-connectivity`]?
- Should a customer defined Proxy configuration used for `containerd`, `cert-manager` and `chart-operator` as well or only for customer workload?

## Current known limitations and issues:

- If customers using a service mesh (e.g. `linkerd`) and the mesh is spawn over multiple WCs, the current implementation provides that all mesh specific member values are defined in the global proxy configuration.
- If a customer want a specific proxy configuration for a workload cluster, this proxy configuration must be currently defined in multiple places.
- If a customer use `kyverno` to inject proxy configuration to all customer related workload, the current [`kyverno-policies-connectivity`] chart will mutate the `chart-operator` `.pod.spec` (managed by `cluster-apps-operator`). 

## Tasks, Stories and PRs

### Tasks

- `mc-bootstrap` behind proxy (implementation in [PR #264](https://github.com/giantswarm/mc-bootstrap/pull/264))
- create workload cluster behind proxy
- create workload cluster behind proxy with user defined proxy details
- document the possible steps if proxy configuration has to be rolling

### PRs

- `mc-bootstrap` behind a proxy ([PR #264](https://github.com/giantswarm/mc-bootstrap/pull/264))
- `cluster-apps-operator` propagates proxy configuration for workload clusters ([PR #290])
- `cluster-cloud-director` refer to a `containerd` proxy configuration secret ([PR #38](https://github.com/giantswarm/cluster-cloud-director/pull/38))
- `cluster-aws` refer to a `containerd` proxy configuration secret ([PR TBD](tbd))
- `cert-manager` accepts `cluster-apps-operator` generated proxy configuration ([PR #270](https://github.com/giantswarm/cert-manager-app/pull/270))
- `chart-operator` ([PR #961](https://github.com/giantswarm/chart-operator/pull/961))

<!-- Links -->
[`cluster-apps-operator`]: (https://github.com/giantswarm/cluster-apps-operator)
[`config`]: https://github.com/giantswarm/config
[`kyverno-policies-connectivity`]: (https://github.com/giantswarm/kyverno-policies-connectivity)
[proxy variables]: https://about.gitlab.com/blog/2021/01/27/we-need-to-talk-no-proxy/
[PR #290]: (https://github.com/giantswarm/cluster-apps-operator/pull/290)
[ClusterAPI]: (https://cluster-api.sigs.k8s.io/#:~:text=Cluster%20API%20is%20a%20Kubernetes,and%20operating%20multiple%20Kubernetes%20clusters.)

<!-- 
toc got created by running 

```
go install sigs.k8s.io/mdtoc@v1.1.0
mdtoc --inplace
```
-->