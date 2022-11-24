# RFC 0015 - CAPI matrix per provider

## Introduction

We have a cluster-<provider> chart for every provider that we support. It has a set of templates that allow our customers to create a cluster app with all necessary resources required by a Cluster API implementation. 

In the values of these charts we define the Kubernetes version of the cluster and the image that machine will use to run. These images contain the Kubernetes components with a specific version. 

One of the goal in this RFC is decouple Kubernetes version from image names so customer does not need to know which image correspond to which version. At the same time we might want to provide new OS version when new CVE appears without necessarily change the Kubernetes version. Finally having a list of kubernetes version certified as ready to be used benefit to disallow users to create cluster in flawy versions.

## User stories

- As a customer, I want to not worry about the kubernetes version and rely on Giant Swarm default version provided.

- As Giant Swarm staff, I don't want to expend time upgrading cluster manually.

- As Giant Swarm staff, I would like to forbid a specific Kubernetes/OS version to be used in case of security constraints.

- As customer, I want to have the option to have a cluster pinned to a version.

## Solution

- Lets have a cluster-<provider> chart release for every Kubernetes version is released. That way our automation can roll upgrades automatically when new version is published

- Lets include a matrix between Kubernetes version and images names in the chart.

```yaml
kubernetesVersionImages:
  v1.22.9: "ubuntu-2004-kube-v1.22.9"
  v1.22.10: "ubuntu-2004-kube-v1.22.10"
  v1.23.3: "ubuntu-2004-kube-v1.23.3"
  v1.23.4: "ubuntu-2004-kube-v1.23.4"
  v1.23.5: "ubuntu-2004-kube-v1.23.5"
```

This will help users to have to think about image names and I same time we can release a new OS version automatically like

```yaml
kubernetesVersionImages:
  v1.22.9: "ubuntu-2005-kube-v1.22.9"
  ...
```

And customers upgrading to this new version will roll machines with the newer OS with same Kubernetes version.

Every time there is a new K8s version or OS version we will (automatically) create a PR to cluster-<provider> charts including the version and potentially changing the default version (if our tests run successfully).

We can also remove Kubernetes/OS version that we found are flawy or problematic in some way.

We have start with [Cluster API OpenStack](https://github.com/giantswarm/cluster-openstack/pull/125).
