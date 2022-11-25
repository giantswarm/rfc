# RFC 0015 - CAPI matrix per provider

## Introduction

We have a cluster-<provider> chart for every provider that we support (it is our UI to the customer). It has a set of templates that allow our customers to create a cluster app with all necessary resources required by a Cluster API implementation. 

In the values of these charts, among all possible parameters we define the Kubernetes version of the cluster and the image that machines will use to run. These images contain the Kubernetes components with a specific version. 

This RFC born out of necessity to automate the cluster upgrades. For that reason team rocket has discussed and found a solution adding a Kubernetes and OS version in each chart release. Today AWS, GCP anf Open Stack providers pinned the Kubernetes/OS version in the chart. Here we propose an extension to give more flexibility and control to Giant Swarm and the customers.

## User stories

- As a customer, I don`t want to worry about the kubernetes version or OS version used by my cluster machines. Just rely on the Giant Swarm default and tested version.

- As a customer, I would like to choose the kubernetes version of my cluster without think which OS AMI correspond to that version.

- As Giant Swarm staff, I want to have the capacity to push new Kubernetes/OS versions and trigger the upgrade automation.

- As Giant Swarm staff, I would like to forbid a specific Kubernetes/OS version to be used in case of security constraints.

- As Giant Swarm staff, I would like to release a new OS version with the same Kubernetes version and roll all customer clusters when a security breach is detected.

## Solution

The solution proposed is to create a cluster-<provider> chart release for every Kubernetes/OS version is released. That way will help our automation to roll upgrades automatically when new version is published.

But we would like to have a list of images attached to every Kubernetes version like:

```yaml
kubernetesVersionImages:
  v1.22.9: "ubuntu-2004-kube-v1.22.9"
  v1.22.10: "ubuntu-2004-kube-v1.22.10"
  v1.23.3: "ubuntu-2004-kube-v1.23.3"
  v1.23.4: "ubuntu-2004-kube-v1.23.4"
  v1.23.5: "ubuntu-2004-kube-v1.23.5"
```

So the customers don't have to think about image names and we can remove Kubernetes/OS versions that are flawed. For example we can change OS version keeping the Kubernetes version the same:

```yaml
kubernetesVersionImages:
  v1.22.9: "ubuntu-2005-kube-v1.22.9"
  ...
```

Every time there is a new Kubernetes version or OS version we will (automatically) create a PR to cluster-<provider> charts including the version and potentially changing the default version (if our tests run successfully).

At the same time if we found a Kubernetes/OS version with a security issue, we can remove the Kubernetes/OS version and enforce customers to upgrade clusters.

We have start with [Cluster API OpenStack](https://github.com/giantswarm/cluster-openstack/pull/125).

__Bonus__: If cluster-<provider> chart is used for companies out of Giant Swarm they can use their own matrix.
