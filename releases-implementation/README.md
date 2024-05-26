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

### 3.2. Creating and maintaining multiple major releases

Our product is being developed for multiple providers, where we currently support 5 of them - AWS (CAPA), EKS (CAPA), Azure (CAPZ), vSphere (CAPV), VMware Cloud Director (CAPVCD). Hopefully we will work with more providers soon (e.g. GCP/GKE).

We also need to support multiple major versions across those providers. Most of managed Kubernetes products support all community-supported Kubernetes versions, meaning the latest 3 minor versions. In our case that would mean 3 major versions, and that is per provider.

Assuming we would like to support at least 2 major versions per provider, and that we work with 5 providers, we would regularly support 10 major versions across all providers. With 6 providers and 3 latest major releases, this number grows to 18 major releases across all providers.

We will also have to maintain the latest vintage major release for some time, until we migrate all existing clusters to the new product.

Being able to quickly and reliably create and deliver new patch and minor releases across all supported major releases is of paramount importance. It is equally important to ensure that provider-independent changes are consistently delivered across all providers.

Some changes, like patches, have to be delivered not only to the latest major release, but also to all previous major releases that are still supported.

Again, we need mechanisms to ensure that all of the above is being done consistently and reliably, otherwise some providers will stay behind, patches will not be delivered to clusters that do not use the latest release, all of which leads to poor development and operations experience for both Giant Swarm staff and our customers.

There is also a question of release notes, how do we create them and where do we publish them.

Finally, do we need a formal way of deprecating and archiving a release?

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

Multiple teams and multiple people are continuously working on all the above and it is indispensable to ensure that all of them have smooth and frictionless development, testing and release experience, so we can increase deployment frequency, reduce lead time for changes and reduce change failure rate. For this to work, we need to be able to develop, test and release almost every change independently of almost all other changes. The team  that have worked on a change should be able to release the change fully independently, without any intervention from the provider-integration or provider-independent KaaS teams.

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

This document proposes to continue using `giantswarm/releases` repository for creating and delivering releases, albeit in a simplified way when compared to the vintage releases. Release resources are used in a minimal way, and cluster-$provider apps continue to be used for deploying workload clusters.

Briefly put, cluster-$provider apps are still deployed in almost exactly same way, with the following few differences:
- In cluster-$provider app manifest, instead of specifying `.spec.version`, we specify `release.giantswarm.io/version` label.
- Information about app version, catalog and dependencies is obtained from the Release resource (during Helm rendering phase).

The core of this proposal is the idea to decouple the app and component versions from the cluster-$provider apps, which will then enable us to have a very scalable process for working with releases, where we can easily create and manage many releases across many providers and develop mechanisms to enforce business logic across all of those.

We will start with showing a slightly simplified version of the Release resource, then explain how it is delivered and finally consumed.

Other parts the `giantswarm/releases` repository that we can continue to use are:
- release notes,
- announcements,
- unit tests for releases (for enforcing various rules about releases).

`requests.yaml` file would be probably deprecated in favour of more scalable and automated process based on GitHub actions and Renovate.

#### 4.1.1. Creating new release

With the current Release CRD definition, we create a Release resource in the following way:
- All apps, both those deployed as App resources and as HelmRelease resources, are added to Release `.spec.apps`. For every app we specify:
	- app name,
	- app version,
	- name of the catalog from which the app is installed (“default” by default), and
	- app’s dependencies.
- Kubernetes version is specified as a `.spec.components` entry,
- Flatcar version and image variant are specified as `.spec.components` entries,
- cluster-$provider app version is specified as a `.spec.components` entry.

With the above in mind, a Release resource that would correspond to the current cluster-aws release would like like this:

```yaml
apiVersion: release.giantswarm.io/v1alpha1
kind: Release
metadata:
  name: v25.0.0
spec:
  apps:
  - name: aws-ebs-csi-driver
    version: 2.30.1
    dependsOn:
    - cloud-provider-aws
  - name: aws-pod-identity-webhook
    version: 1.14.2
    dependsOn:
    - cert-manager
  - name: capi-node-labeler
    version: 0.5.0
  - name: cert-exporter
    version: 2.9.0
    dependsOn:
    - kyverno
  - name: cert-manager
    version: 3.7.5
    dependsOn:
    - prometheus-operator-crd
  - name: chart-operator-extensions
    version: 1.1.2
    dependsOn:
    - prometheus-operator-crd
  - name: cilium
    version: 0.24.0
  - name: cilium-crossplane-resources
    version: 0.1.0
  - name: cilium-servicemonitors
    version: 0.1.2
    dependsOn:
    - prometheus-operator-crd
  - name: cloud-provider-aws
    version: 1.25.14-gs2
    dependsOn:
    - vertical-pod-autoscaler-crd
  - name: cluster-autoscaler
    version: 1.27.3-gs8
    dependsOn:
    - kyverno
  - name: coredns
    version: 1.21.0
  - name: external-dns
    version: 3.1.0
    dependsOn:
    - prometheus-operator-crd
  - name: metrics-server
    version: 2.4.2
    dependsOn:
    - kyverno
  - name: net-exporter
    version: 1.19.0
    dependsOn:
    - prometheus-operator-crd
  - name: network-policies
    version: 0.1.0
    catalog: cluster
  - name: node-exporter
    version: 1.19.0
    dependsOn:
    - kyverno
  - name: vertical-pod-autoscaler
    version: 5.1.0
    dependsOn:
    - prometheus-operator-crd
  - name: vertical-pod-autoscaler-crd
    version: 3.0.0
  - name: etcd-k8s-res-count-exporter
    version: 1.10.0
    dependsOn:
    - kyverno
  - name: observability-bundle
    version: 1.3.4
    dependsOn:
    - coredns
  - name: k8s-dns-node-cache
    version: 2.6.2
    dependsOn:
    - kyverno
  - name: security-bundle
    version: 1.6.5
    catalog: giantswarm
    dependsOn:
    - prometheus-operator-crd
  - name: teleport-kube-agent
    version: 0.9.0
  components:
  - name: cluster-aws
    version: 1.0.0
  - name: flatcar
    version: 3815.2.2
  - name: flatcar-variant
    version: 3.0.0
  - name: kubernetes
    version: 1.25.16
  date: "2024-05-18T12:57:50Z"
  state: active
```

New releases are added via pull requests in the same way like vintage releases. After a pull request is merged, CircleCI job pushes the newly added Releases to the releases catalog and to the provider-specific app collection.

#### 4.1.2. Deploying a cluster

Today workload clusters in our Cluster API-based KaaS product are deployed with cluster-$provider apps. That remains the same, with only one minor difference, which is how we specify the version, where instead of specifying App’s `.spec.version` property we specify `release.giantswarm.io/version` label and leave `.spec.version` empty.

So the whole manifest for the cluster-$provider app and its config would look like this:

```yaml
---
apiVersion: v1
data:
  values: |
    global:
      metadata:
        name: mycluster
        organization: mycompany
        description: Production cluster
kind: ConfigMap
metadata:
  creationTimestamp: null
  labels:
    giantswarm.io/cluster: mycluster
  name: mycluster-userconfig
  namespace: org-mycompany
---
apiVersion: application.giantswarm.io/v1alpha1
kind: App
metadata:
  labels:
    app-operator.giantswarm.io/version: 0.0.0
    release.giantswarm.io/version: 25.0.0
  name: mycluster
  namespace: org-mycompany
spec:
  catalog: cluster
  kubeConfig:
    inCluster: true
  name: cluster-aws
  namespace: org-mycompany
  userConfig:
    configMap:
      name: mycluster-userconfig
      namespace: org-mycompany
  version: ""
```

After cluster-$provider app is deployed, few things will happen:
- an App mutating webhook reads the release version, looks up the corresponding release, reads cluster-$provider app version from it and finally it sets App’s `.spec.version` property,
- after cluster-$provider app is applied successfully, in order to render all templates and set the app version, catalog and depends on properties, Helm will do the following:
	- it will lookup the App resource (via Helm `lookup` function) and read release version,
	- then it will lookup the Release resource and read app version, catalog and depends on properties from there, and
	- finally it will render all templates and apply them.

From this point forward, everything is the same like when all app details were set directly in the Helm chart.

### 4.2. Comparison with the current releases

This section compares the proposed release process with the current one, where we deploy clusters with cluster-$providers apps which have information about app versions.

We cover some of the topics mentioned in section 3. Motivation.

#### 4.2.1. Release identifier and versioning

TBA

#### 4.2.2. Creating and maintaining multiple major releases

TBA

#### 4.2.3 Development and testing

TBA

#### 4.2.4. Multiple release models and release channels

TBA

[RFC2119]: https://datatracker.ietf.org/doc/rfc2119/
[RFC8174]: https://datatracker.ietf.org/doc/rfc8174/
