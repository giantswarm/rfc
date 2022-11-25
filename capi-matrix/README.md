# Cluster API Kubernetes/OS version management

## Introduction

We have a cluster-PROVIDER app for every provider that we support (it is our interface to define the cluster structure and configuration). It has a set of templates that allow our customers to create a cluster app with all necessary resources required by a Cluster API implementation. 

In the values of these charts, among all possible parameters we define the Kubernetes version of the cluster and the machine image (AMI) that will be used to run the VMs. These images contain the Kubernetes components with a specific version. There are usually three AMIs defined in every provider: bastion, control-plane and node pools.

This RFC born out of necessity to automate the cluster upgrades. For that reason, team Rocket has discussed and found a solution adding a Kubernetes and OS version in each chart release. Today AWS, GCP anf Open Stack providers pinned the Kubernetes/OS version in the chart. Here we propose an extension to give more flexibility and control to Giant Swarm and the customers.

## User stories

- As a customer, I don't want to worry about the kubernetes version or OS version used by my cluster machines. Just rely on the Giant Swarm default and tested version.

- As a customer, I would like to choose the kubernetes version of my cluster without think which OS AMI correspond to that version.

- As Giant Swarm staff, I want to have the capacity to push new Kubernetes/OS versions and trigger the upgrade automation.

- As Giant Swarm staff, I would like to forbid a specific Kubernetes/OS version to be used in case of security constraints.

- As Giant Swarm staff, I would like to release a new OS version with the same Kubernetes version and roll all customer clusters when a security breach is detected.

## Solution

The solution proposed is to create a cluster-PROVIDER chart release for every Kubernetes/OS version is released. That way will help our automation to roll upgrades automatically when new version is published.

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

Every time there is a new Kubernetes version or OS version we will (automatically) create a PR to cluster-PROVIDER charts including the version and potentially changing the default version (if our tests run successfully).

At the same time if we found a Kubernetes/OS version with a security issue, we can remove the Kubernetes/OS version and enforce customers to upgrade clusters.

We have start with [Cluster API OpenStack](https://github.com/giantswarm/cluster-openstack/pull/125).

__Bonus__: In favour of making the providers apps not tied to Giant Swarm, adding the conversion image table helps enabling other vendors to adopt it and customize it.

## How the conversion image table is updated?

- We have not defined this process. But one possible scenario would be:

1) Kubernetes/Kinvolk release a new OS/k8s version

2) Our image builder job is triggered and creates the AMIs for the different providers. 

3) Other job can be triggered after and create pull requests to the cluster-PROVIDER repos adding the new k8s/OS version.

4) Our future CI pipeline can test this new version for each provider and check it runs correctly (conformance tests or even custom tests). 

5) In case CI succeed the default version and conversion image table is changed to the new one with the approval of the owning team.

From this moment Cluster Upgrade automation can start scheduling the workload cluster upgrades based on customer constraints. More info about this process discussed [here](https://github.com/giantswarm/rfc/pull/52).

## Open questions

- Every time we release a new provider app with a newer Kubernetes version we can make it default, but at the same time we might want to wait and run not edge version but a previous one. So we will need a bit of process deciding when we change the default version.

## Out of scope

- How containerd version is managed.

- How default apps version is managed.
