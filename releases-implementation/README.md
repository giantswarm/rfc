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

### 3.2. Creating and maintaining multiple releases

Our product is being developed for multiple providers, where we currently support 5 of them - AWS (CAPA), EKS (CAPA), Azure (CAPZ), vSphere (CAPV), VMware Cloud Director (CAPVCD). Hopefully we will work with more providers soon (e.g. GCP/GKE).

We also need to support multiple major versions across those providers. Most of managed Kubernetes products support all community-supported Kubernetes versions, meaning the latest 3 minor versions. In our case that would mean 3 major versions, and that is per provider.

Assuming we would like to support at least 2 major versions per provider, and that we work with 5 providers, we would regularly support 10 major versions across all providers. With 6 providers and 3 latest major releases, this number grows to 18 major releases across all providers.

Additionally, it might be possible that for every major release, we would support more than 1 minor in some cases (e.g. last 2). Therefore, when there is a new patch version of some app (e.g. a security fix), we can easily be in a situation where we have to create a double-digit number of new patch releases in order to patch all affected minor releases.

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

With the current cluster-$provider apps releases process, the cluster-$providers app version is the release identifier.

With the releases repository, release identifiers would be defined in the repository itself, in the same way like for vintage releases. In this process the cluster-$provider app is one of the release components.

In both cases there is a single release identifier, just defined in different places.

Versioning logic, i.e. what and how can change in a major, minor  or a patch version, would be the same in both cases.

#### 4.2.2. Creating and maintaining multiple releases

Today, with the current cluster-$provider apps releases process, we only support the latest version of the cluster-$provider app. However this will change now, as we will have to support multiple major releases (e.g. to support multiple Kubernetes versions).

As described in section *[3.2. Creating and maintaining multiple releases](#32-creating-and-maintaining-multiple-releases)*, we will be in a situation where we are supporting 10 or more major releases across all providers (5-6 providers, 2-3 major release per provider). In order to maintain all those major releases:
- We need one cluster-$provider app git branch per major release, so for 10 major releases this means 10 git branches (across multiple repos).
- We also need one git branch for every major version of the cluster chart.
- In case we want to support more than 1 minor version for every  major, the number of git branches is even larger.

##### 4.2.2.2. Scenario 1: new provider-independent app patch

Now in the case above, let’s say we want to release a new patch version for some provider-independent app, and we have to do that in 5 providers, and for 2 major releases for every provider. The process would look like the following:
- Renovate updates the version of the app in 2 git branches in the cluster chart. Here we have 2 pull requests, both created by Renovate.
	- In case the patch is a change in the cluster chart itself (and not a new app patch version bump), we would have 1 PR to make the change in the main branch, and another PR to cherry-pick the change to the previous major version branch. Overall even more work then when “just” releasing new app patch versions.
- We release new patch versions for the last 2 major releases of the cluster chart. Here we have 2 release pull requests, both triggered manually by pushing a new branch which then triggers the CI that opens the release pull request.
- For all 5 providers, Renovate opens PRs for the last 2 major versions. Here we have 10 PRs opened by Renovate.
- We release new patch versions for the last two major releases of all cluster-$provider apps. Here we have 10 release pull requests.

In total, in the above scenario, we have 12 Renovate PRs and 12 release PRs, so 24 PRs in total. And all these PRs are across multiple components owned by multiple teams, meaning the some actions should be taken by people from multiple teams.

The above example might seem like exaggerated. Even if you cut it in half, 12 PRs is still a lot of work.

Even in one of the simplest and common scenarios, where a simple provider-independent app patch is delivered to just the latest major version of 5 providers, we would have:
- 1 Renovate PR to bump the app version in the cluster chart,
- 1 release PR to release the change in cluster chart,
- 5 Renovate PRs to bump the version of the app in all cluster-$provider apps,
- 5 release PRs to release a new patch version of all cluster-$provider apps.

Here we still have to deal with 12 pull requests. Before we have introduced the cluster chart, it would be 10 PRs in default-apps-$provider repos, so 2 PRs less, but that a minor difference.

Now let’s see how the above scenario would look like in a release process where releases repository is used. When a new app patch version is releases:
- We open 1 PR in the releases repository and in that PR we add new Releases for every affected major version of every provider.

That’s it - 1 PR. 1 PR for any number of releases across any number of providers.

We can also maintain a draft PR in the releases repository where we automatically create next draft releases for all providers, and then Renovate can bump version numbers in those draft releases, and we just decide when to cut the new release (and name it appropriately).

##### 4.2.2.3. Scenario 2: change in cluster-$provider app

Let’s say we have a change in cluster-aws, and we want to patch the latest 2 major releases with that change. Currently, with cluster-$provider apps, we would have to:
- do the change in the main branch for the latest major release,
- cherry-pick the change to the previous major release branch,
- open 2 release PRs.

4 PRs in total. Not too horrible, if done infrequently.

Just how often we would have to do this? At what point the cherry picking becomes a tedious burden full of git conflicts because the latest major have diverged compared to the previous one?

Now let’s see how the above scenarios would look like with the releases repository. Here a single major cluster-aws version can be used in multiple major release (unless the cluster-aws itself had a breaking change in a new major release, so cluster-aws itself has a new major version in a new major release).

Assuming we’re working with a single major version in the latest 2 major releases, we would have to:
- do the change in the cluster-aws main branch for the latest major release,
- 1 release PR in cluster-aws,
- 1 PR in the release repository to create new releases with the new cluster-aws version.

Compared to the cluster-$provider app releases, here we have 1 PR less, which is not crucial here. What can make a large difference is the possibility to use a single cluster-aws major version across multiple major releases, which drastically reduced the need for cherry picking cluster-aws changes across multiple git branches.

Worst case scenario, if cluster-$provider app had a breaking change itself, and a new major release also has a new major version of cluster-$provider app, the process is similar in both cases, with the difference that in the case of releases repository there is 1 PR more (to create Releases in the releases repository). However, with all app and component versions being outside of cluster-$provider app, and with a more careful approach where new features are opt-in and added behind Helm values and more attention is given to backward compatibility, the possibility of having a breaking change in cluster-$provider app is reduced to a minimum.

#### 4.2.3. Development and testing

With app versions being in cluster-$provider apps, almost all changes are done in a single place - in the cluster-$provider app.

When a team wants to add new app version to the next release, they have to bump the app version in the cluster-$provider app (or in the cluster chart). This app version bump will get merged. Since many different types of change are done in the same repo, in addition to app version bump, the next release of the cluster-$provider app will probably contain not just the new version of the app, but also other Helm chart changes as well. Therefore a simple change such as releasing a new app patch version gets entangled with many other types of changes, which adds friction during development, testing and releasing.
- When the app version bump is tested, it is not necessarily tested on top of the latest release, but actually on top of the latest release plus multiple merged, but unreleased changes in the cluster-$provider app.
- After the app version bump is merged, it may be released right away, but it may also take some time until it is released, depending on the current state of the cluster-$provider app repo and what unreleased changes it has.
- Here the team that owns the app is dependant on the provider-integration team and/or on the provider-independent team, because they are needed for the PR reviews and the new release. This practically means that the team that owns the app does not fully own the delivery of the app. More cross-team reviews, more cross-team communication required, more friction.

Now let’s see how the above scenario would look like with the releases repository.
- The team that owns the app opens a new PR in the releases repo where they create one or more new releases.
- In the simplest case, app version bump is the only change in the new releases, so it is tested and delivered fully independently.
- In case there is an existing/draft PR in the release repo where new releases are being added with new versions of other apps, that existing PR can be updated.
	- If there is a need to have the new app version tested and delivered ASAP, e.g. in case of CVEs, the existing/draft releases repo PR does not have to be updated, and another PR can be created specifically for the new app version (after this the previously created PR can be rebased/updated).
- The delivery of the new app versions is not entangled with the delivery of cluster-$provider app Helm chart changes.
- The team that owns the app can create the new release on their own and they do not need to ask other teams for the review/approval, since the unit tests in the releases repository verify that the newly created releases respects the defined release rules, e.g. new app patch delivered to all providers, new app minor must be delivered in a new minor release, etc.

#### 4.2.4. Multiple release models and release channels

TBA

[RFC2119]: https://datatracker.ietf.org/doc/rfc2119/
[RFC8174]: https://datatracker.ietf.org/doc/rfc8174/
