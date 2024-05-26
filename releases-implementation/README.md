---
creation_date: 2024-05-26
issues:
- TBA
owners:
- https://github.com/orgs/giantswarm/teams/sig-architecture
- https://github.com/orgs/giantswarm/teams/team-turtles
state: approved
summary: Where and how we implement releases for workload clusters.
---

# Releases implementation

## 1. Introduction

This RFC defines how we implement releases for workload clusters for the new KaaS product that is based on the Cluster API project. It covers multiple aspects of releases, such as creation, testing and delivery of releases. It does not cover how clusters are upgraded to the new releases.

## 2. Requirements language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC2119] [RFC8174].

## 3. Motivation

New Giant Swarm Managed Kubernetes product, which is using Cluster API as one of the foundational technologies for deploying workload clusters, is improving our Kubernetes platform in many aspects. While the platform is being improved, at the moment of writing this document, and as we’re getting close to production readiness of the product, there are still many unknowns around releases and how they will work.

As we have been developing the new Giant Swarm Kubernetes platform, we have moved away from old releases concept that we had in our vintage product towards a more flexible and robust way of releasing and upgrading to new versions, or at least that was the intended goal. Now, the closer we are getting to the production readiness of our new product, the more unknowns we have and the more shortcomings of the new releases we realise.

### 3.1. Release identifier and versioning

We have noticed that we miss few aspects of old releases, like a single release identifier, being able to easily and clearly see which versions of which apps are part of some release and which versions of which apps should be deployed to a workload cluster.

We also missed a versioning scheme where it’s clear what we promise and what you can expect in a patch, minor or major release upgrade, which, although not strictly defined, it was mostly clear for releases of the vintage product. And equally important, we lack a mechanism to enforce this behaviour.

### 3.2. Managing multiple major releases

Our product being developed for multiple providers, where we currently support 5 of them - AWS (CAPA), EKS (CAPA), Azure (CAPZ), vSphere (CAPV), VMware Cloud Director (CAPVCD). Hopefully we will work with more providers soon (e.g. GCP/GKE).

We also need to support multiple major versions across those providers. Most of managed Kubernetes products support all community-supported Kubernetes versions, meaning the latest 3 minor versions. In our case that would mean 3 major versions, and that is per provider.

Assuming we would like to support at least 2 major versions per provider, and that we work with 5 providers, we would regularly support 10 major versions across all providers. With 6 providers and 3 latest major releases, this number grows to 18 major releases across all providers.

We will also have to maintain the latest vintage major release for some time, until we migrate all existing clusters to the new product.

Being able to quickly and reliably create and deliver new patch and minor releases across all supported major releases is of paramount importance. It is equally important to ensure that provider-independent changes are consistently delivered across all providers.

Some changes, like patches, have to be delivered not only to the latest major release, but also to all previous major releases that are still supported.

Again, we need mechanisms to ensure that all of the above is being done consistently and reliably, otherwise some providers will stay behind, patches will not be delivered to clusters that do not use the latest release, all of which leads to poor development and operations experience for both Giant Swarm staff and our customers.

### 3.3. Development and testing

We deploy workload clusters by gluing together multiple components. Some of those are:
- Provider-independent Cluster API resources (e.g. Cluster, MachineDeployment/MachinePool, etc.),
- Provider-specific Cluster API resources (e.g. AWSCluster, AzureCluster, VSphereCluster, VCDCluster),
- CPI implementation (aka provider-specific cloud controller manager),
- CNI (e.g. Cilium),
- CSI,
- upstream apps that we package,
- our apps that we develop and package,
- provider-independent and provider-specific default configuration of apps,
- configuration of the operating system and different node components, such as systemd, containerd, etc.

Multiple teams and multiple people are continuously working on all the above and it is indispensable to ensure that all of them have smooth and frictionless development, testing and release experience, so we can increase deployment frequency, reduce lead time for changes and reduce change failure rate.

### 3.4. Does one-size-fits-all releases really work?

We have different customers that all have different businesses and different needs.

Can the same way of doing releases really work equally well for both a fast-growing startup and a large corporation?

Can the same way of doing releases really work equally well for, one one hand, a retail company that has fully embraced cloud-native approach, and on the other hand a manufacturer that is deploying Kubernetes clusters to multiple on-premise slow-changing and almost air-gapped environments like factories?

We and our customers also run different types of clusters.

Can the same way of doing releases really work equally well for both development and production clusters, both ours and from our customers?

Can the same way of doing releases really work equally well for both workload and management clusters?

The answer to all above questions is probably ranging from “probably not” to a clear “no”.

A fast-growing startup can probably move faster with less ceremony and practice even continuous deployment, compared to a large corporation which may have more processes and even limitations so it is moving at slower speed, meaning that may have more requirements around how often they do which type of upgrades (e.g. patch vs minor vs major).

A retail company that has fully embraced cloud-native approach can move at higher speeds and, similarly to a fast-growing startup, they can be able to deploy new releases very quickly, thanks to their approach to building, deploying and managing applications. OTOH a manufacturer may require less frequent feature upgrades that are performed during infrequent and narrow maintenance windows, maybe even just a few or a handful of times per year, and then more frequent patch upgrades, and all of those can be highly dependent on the on-premise infrastructure and existing processes in their factories. In some cases even something similar to a long-term support releases (LTS) maybe be required, so that older versions are supported for the extended periods of time (similarly to [Microsoft AKS LTS](https://learn.microsoft.com/en-us/azure/aks/long-term-support) and [Amazon EKS extended support](https://aws.amazon.com/blogs/containers/amazon-eks-extended-support-for-kubernetes-versions-pricing/)).

Some companies may want to upgrade apps faster and more often than Kubernetes and operating system, because the former is less impactful to their workload than the latter and they do not require the latest Kubernetes and OS versions, but are satisfied with any supported and stable version. Others may not care about it and they would like to get newer versions of everything equally fast, or they want the latest Kubernetes releases to be deployed as soon as possible.

To accommodate the needs of different types of businesses, we may need not one, but at least few different **release models**, so that customers can choose which one is working the best for their use case.

In addition to all the above, even for a single release model, it may not be a good idea to make new releases available to all clusters at the same time, so it can be useful to have different **release channels**, where some release channels are getting new releases faster than the others. E.g. see [GKE release channels](https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels). A development cluster may use a faster release channel, while a production cluster may use a slower one. Some companies may use faster release channel for all their clusters, while others may use a slower one similarly for all their workload.

## 4. Proposal

This section defines how releases are implemented, where they are, how they are developed, tested and delivered.

Then it compares the proposed solution to the current one that we have for our new KaaS product that is based on Cluster API.

### 4.1. Implementation of releases

TBA

### 4.2. Comparison with the current releases

TBA

[RFC2119]: https://datatracker.ietf.org/doc/rfc2119/
[RFC8174]: https://datatracker.ietf.org/doc/rfc8174/
