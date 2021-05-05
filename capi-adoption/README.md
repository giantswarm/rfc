# Road to Cluster API (over the potholes)

## About

This is a document to present some of the fundamental problems we have faced when trying to adapt Giant Swarm release management and operator reconciliation practices to upstream Cluster API controllers. We present the way upstream approaches it and provide a proposal to change our direction into an upstream compatible model.

## Present state of Giant Swarm platform

The present state of Giant Swarm platform consists of a single management cluster on each installation. All workload clusters are managed from the same management cluster on a given installation.

Different release versions of workload clusters are managed by running sets of releases on every management cluster. Each release consists of a set of operators which are reconciling CRs that are labeled to use that given release. Most of the time this worked pretty well for us, given the cost savings that it brought. It also helped us to take control of the lifecycle of the different clusters living on those management clusters, allowing us to upgrade every cluster independently by just changing the label in the CRs.

We were able to utilize a small number of nodes, run our own configuration of kubernetes and still manage a big number of workload clusters run on different versions.

![Multi-version state](<image>)

## Problems with the Giant Swarm approach

### Versioning of operators with labels

Our current approach to running multiple versions of the same operator on the same cluster is based on CR labels. This has worked very well until we started deploying admission controllers and later deploying upstream controllers for CAPx.

The nature of upstream CAPI is such that a single workload cluster consists of several different CRs. There can be easily 20 of them and they all must share interrelated references between each other. Some of these are automatically created as part of the reconciliation and this creates big challenges for catching the event at the right point and applying the right Giant Swarm specific labels so that versioned operators can find them. For example, during our upgrade process it’s hard to validate the contents of the labels (is it the wrong value or are we in the middle of an upgrade?) or even determine the order in which the labels must be updated so that the right operators pick up the CRs.

Another problem with label based versioning is that because all code in the upstream ecosystem has been built on the idea of having a single version of an operator on a given cluster, there are several optimizations that leverage this fact. For example, kubebuilder (a widely used framework) has internal re-queuing logic that will repeat reconciliation of a given CR at certain states and this bypasses completely any label filtering. Whether it is built as a label selector for watch operation or post-processing predicate filter as is the current situation with our forked controllers. This has a consequence that change of version label on any given CR does not guarantee that the change is immediately reflected on which operators are reconciling it. In fact, there would often be multiple of them which is very risky.

Along with operators, admission controllers also must support versioning. Due to the nature of webhook architecture and Kubernetes api-server behavior, they introduce an increased risk for cluster lockup because the upstream approach is to only run one webhook at a time on a cluster, but we must ensure that only certain instances of different admission controllers actually do receive the webhook callback. Otherwise there’s risk that a webhook of some older release is crashing on a newer object and blocks the whole operation.

It is also not straightforward to reason about webhooks and how to ensure that some of them only reconcile certain CRs. Currently on Azure we already use upstream CRDs to reconcile workload clusters and therefore azure-admission-controller is defaulting and validating the same CRDs that the upstream webhook would once the clusters are migrated to CAPZ release. It took extensive efforts to find a reliable logic for different label combinations that would work for both cluster flavors because currently the requirements for CR content are very different between Giant Swarm implementations and CAPZ.

When configuring multiple admission controllers to process the same CRs, there is no guaranteed execution order. Currently the primary ordering is implemented with alphabetical sorting, but this is not a documented contract or public API so this could change at any point in the future. Because customers have now full CP API access and it’s even encouraged that they involve themselves with cluster administration, it can happen that a certain combination of CR content is used which then causes Giant Swarm admission controllers to conflict with upstream controllers. Results of these are undefined.

### Versioning of CRDs

Cluster API is still in a very early stage of development and its CRD versions change once or twice a year. Kubernetes api-server can only manage one CRD version at a time as a storage version and backwards and upwards support for alternative versions must be implemented by appropriate webhooks. Depending on the change in a CRD structure these webhooks work or not.

Currently the stable API version for Cluster API is v1alpha3 but v1alpha4 is already well under development. It is highly possible that when we get our first production ready version of GS managed Cluster API released, we soon must migrate to the next one involving CRD migration. This can become very problematic when the management cluster has a large number of active releases that contain components that utilize different versions of CRDs.

### Operator reconciliation approach towards resource management

At Giant Swarm a very unique thing we do with these cluster related controllers is that deploying a version of the controllers in most cases leads to a direct impact on the infrastructure resources it is managing in the form of an upgrade.
This is very different from upstream and other community operators where usually an upgrade of the controller SHOULD NOT touch anything on the resource side, but any resource change is usually explicitly affected by a change in a field or annotation, e.g. by changing the prometheus version in a CR that prometheus operator manages or by changing the kubernetes version in a controlplane CR for CAPI.

This is also more in line with native K8s controllers, where a new Deployment controller does not roll all deployments for example. It might offer new opt-in features that you can use, but you have to do that explicitly.

### Immutable release of all components

As briefly mentioned earlier in this document, the Giant Swarm releases are currently strictly defining all specific components that are either needed to create a workload cluster or that are running on the workload cluster. This includes operators running on management cluster, used Flatcar image version, installed Kubernetes version and several apps for both management cluster and workload cluster.

When we move to fully use upstream Cluster API controllers to manage workload clusters, the whole concept of versioning changes radically. With the Cluster API CRDs and the upstream controllers, the end-user gets a much more flexible way to create, configure and manage workload clusters. At the same time the mechanisms how different components are configured, changes dramatically.

#### Managed Apps for workload cluster

There is already ongoing discussion & work towards separating managed apps of workload cluster from the release of the given cluster. This way the apps are managed solely on the workload cluster similar to any other customer deployed workload.

#### Kubernetes version and core components of a workload cluster

With full upstream Cluster API implementation, the used Kubernetes version is configured as part of the bootstrap CRs. When the kubernetes version of the workload cluster needs to be changed, only a change to said CRs is needed.

If the Kubernetes version would be tied into a release like it used to be, this would severely limit customers’ flexibility for testing & working on different workload clusters. Similarly to Kubernetes version, the operating system used for the nodes can be configured on the CRs, and the core components of the workload cluster can be also configured as part of the bootstrap operator CRs. This includes e.g. etcd and used cluster DNS servers.

#### Management Cluster Operators

When running with multiple versions of operators on a shared management cluster, we configure the specific version of the involved operators in a release. This was done to be able to control when changes to infrastructure resources would be done, by handling the reconciliation of the CRs from one release to another one. With upstream Cluster API implementation this doesn’t make as much sense anymore.

As mentioned earlier, the upstream approach to controller implementations has always been such that change of controller version must not affect the reconciled resource unless the CR requires so. Therefore there’s less reason to define the version of controllers in a way of a release because when the controllers are running the shared CRD version anyway, they would effectively behave the same unless the CR specifically requires otherwise.

### Future Releases

Given how adoption of upstream Cluster API changes the nature of cluster components’ version management, it doesn’t make sense to have old style Giant Swarm releases anymore.

We should have a certain level of defaulting for a set of versions we know to work well together, but we must not restrict customers from leveraging the flexibility of Cluster API.

When we have already agreed to perform automatic minor and patch upgrades, we can equally just adopt the upstream workflow and update management cluster controllers in-place.

## Proposal for alternative approach to provide Giant Swarm platform with upstream Cluster API

To pick up the key points from current problems and to fully align with upstream in order to simplify our daily work and allow customers more flexibility while improving stability, here are proposed steps forward.

### Let go of releases and multiple versions in same management cluster

Currently the major source of friction with upstream and the source of complexity on our platform is coming from immutable releases and the need to run multiple versions of everything in the same Kubernetes cluster.

Since the upstream Cluster API drastically changes the way how things are configured, we should leverage it, not work against it. Even though we have managed to contribute code upstream to support our use case, the community sees these contributions as workarounds to avoid blocking us. But we’d be always going in a different direction, increasing the effort and cost to fully implement CAPI and be aligned with the project.
There are less risks for failure when different parts are managed separately and when active change of resources is always a direct consequence of active change on CR[s]. Management cluster operators can be upgraded when there are fixes, but they must not automatically change any of the reconciled resources. When there is a hot security fix for Kubernetes, it’s enough to update only the Kubernetes version. When workload cluster applications need updating, customers can perform it at their will via our App management infrastructure.

Instead of strictly trying to keep control of release components, we should have sane defaults for CR templating. This would be our way to indicate “we have tested these components in this combination and found them to be rock solid, use them”.
Focusing on templating with sane defaults rather than enforcing certain values would also mean getting rid of admission controllers that we currently use to validate and default CR content, simplifying the Kubernetes configuration.

Allowing customers to customize those sane defaults would ease the testing of new combinations. For example, since upgrading Kubernetes to a new version would be only a matter of changing the required CRs, customers can test their workloads running on the new Kubernetes version on the cluster they decide at their own pace. And they would be testing that change in isolation. There would be no changes in the infrastructure resources or the installed apps.

### Change our mindset when implementing operators

In order to comply with upstream operator behavior, we must change our mindset when implementing operators. Instead of writing logic that proactively changes reconciled resources immediately when the code is executed, we should adopt the approach where only change in the CRs can cause an action on the target resource.

### Run multiple management clusters when needed

Getting rid of releases means that different Kubernetes or Apps versions can co-exist on the same management cluster. When our management cluster only consists of a stable bunch of operators that are regularly patched and supplemented with additional features, they also occasionally need bigger upgrades. Most of the time this happens when the upstream CRDs are bumped into next apiVersion. For these purposes, we want to run multiple management clusters where customers can try the new major versions of components ahead of time and verify that their integrations work as expected. When the time eventually comes for the major upgrade, we should be able to execute it in-place on the existing management cluster because upstream already provides full support for CRD migrations via conversion webhooks. [The Kubernetes CRD versioning also guarantees that existing CRs stored on old versions are not migrated until actively requested.](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#writing-reading-and-updating-versioned-customresourcedefinition-objects)

#### Provisioning

For this reason, creating new management clusters should be an easy and effortless task. In this case, using CAPI to manage our management clusters seems like a good fit. It wouldn’t just be easy to create and manage our clusters, but we would be dogfooding the components that our solution is based on.
The first management cluster in an installation can be bootstrapped following the [Bootstrap & Pivot approach recommended by CAPI.](https://cluster-api.sigs.k8s.io/clusterctl/commands/move.html#bootstrap--pivot) Additional management clusters that are required in the same installation can be created normally in the existing cluster.
We can leverage the CAPI integration with cloud provider offerings to try reducing costs.

#### Configuration

Our present deployment pipeline has gone through several design and implementation iterations and it has been developed continuously to support new use cases especially for managed apps.

While working very well in the present configuration, it becomes problematic when we need to separate the concept of installation from a management cluster and allow easy creation of new management clusters.

Currently it’s not possible to deploy basic core components on top of a vanilla Kubernetes cluster without access and dedicated configuration in installations repo and use of opsctl tool that is built to render the configuration for further steps in deployment.

CAPI management clusters [are configured with a simple command.](https://cluster-api.sigs.k8s.io/clusterctl/commands/init.html) Similarly, we need to provide a way to install GiantSwarm core components.
