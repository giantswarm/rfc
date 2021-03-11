# RFC 0015 - Automatic workload cluster upgrades

## User stories

- As a Giant Swarm customer, and also as Giant Swarm, we would like to have workload clusters running in the latest version automatically, and not worry about patching security vulnerabilities or cluster components running out of updates (e. g. Kubernetes release end of life).

- As a customer admin, I would like to define maintenance windows to ensure workload clusters are only upgraded within these hours.

- As a customer admin, I would like to mark a workload cluster as "frozen" in order to block upgrades for a certain time period.

- As a customer admin, I want to define the upgrade order of clusters, so that certain workload clusters are upgraded to a distinct workload cluster release before others are.

- As a user I want to schedule an upgrade on a certain day/time.

- As a customer, and also as Giant Swarm, we want to capture the result of an upgrade. Based on the result we can alert on a certain condition, track the history for certain cluster(s) or automate response based on the end state.

## Reasoning

Our customers need to plan every upgrade on their side and manage the upgrades for every workload cluster release. Each customer has their own requirements regarding when they need to schedule upgrades (freeze periods, maintenance windows, etc.). At the same time, cloud native projects and Giant Swarm are continuously providing new releases. The preparation and execution of upgrades is time and labor intensive, while the fact that they are executed manually does not add much value to stakeholders.

Giant Swarm designed a versioning scheme (based on Semver), which includes all components on the stack, to ensure idempotence and expose the level of impact that changes bring to the customer. Patches and Minor releases should have no impact on the customer workloads, which means that they can be applied in the environments at any time.

## Current state

Right now the automatic upgrades are carried by Solution Engineers agreeing with the customer on upgrade windows and environments selection. The idea is to automate all this behavior and information under a Kubernetes operator(s) and Custom Resource(s).

The Solution engineer plans cluster upgrades based on cluster type (environment, team,...) and maintenance windows offered by the customers. The upgrade is just a change on the cluster version field on the cluster Custom Resource (CR).

Based on the fact Giant Swarm is moving to Cluster API this is story let us define a new greenfield scenario where we can design a model that can be more generic and not focus only in Giant Swarm platform. The idea would be contribute as much as possible with upstream due the fact most of this functionality would be useful for everyone that manages clusters.

## Concepts


### Cluster upgrade entity

There are different reason why we are interested in having an object to define the upgrade intent. 

- As we define in the user stories, we/customers would like to schedule upgrades on certain date from running version to a specific one. That way customer can plan upgrades ahead and so do we.

- We have a registry of upgrades done to a cluster for auditing and tracking purposes.

- We can save cluster upgrade status displaying if something goes wrong or not.

- In theory we can include apps upgrades together or separately.

### Upgrade policy entity

Our customer can have a different set of constraints when it comes to allow changes in their clusters. The upgrade policy would define those and then the clusters can rely on a policy to enforce the desired behavior.

The upgrade policy would be possible to be referenced from different cluster resources (Cluster,Machine Pool, KubeadmControlPlane, Apps,...) letting controllers to decide if the resource would be or not reconciled.

The upgrade policy would contain

- A way to define dates or times where clusters (or relatives) can be modified.

- A way to define dates or times where clusters (or relatives) cannot be modified.

## Technical aspects

We envision aforementioned concepts would become custom resource definitions and there will be additional controller that would enhance and ensure the correct behavior.

### Resources

#### ClusterUpgrade

Example resource:

```yaml
apiVersion: 
kind: ClusterUpgrade
metadata:
  name: upgrade-to-release-v20
  namespace: default
spec:
  clusterRef:
    apiVersion: cluster.x-k8s.io/v1alpha3
    kind: Cluster
    name: foo01
  kubernetesVersion: 1.19.8

#### UpgradePolicy

Example resource:

```yaml
apiVersion: 
kind: UpgradePolicy
metadata:
  name: working-hours-except-month-start
  namespace: default
spec:
  maintenanceWindows:
  - name: working-hours
    startTime: 2021-03-10T07:00:00Z
    endTime: 2021-03-10T17:00:00Z
    recurrence: FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
  maintenanceExclusions:
  - name: month-start
    startTime: 2021-03-01T00:00:00Z
    endTime: 2021-03-10T23:59:59Z
    recurrence: FREQ=MONTHLY

This would allow upgrades to happen between 07:00 UTC and 17:00 UTC on Monday-Friday, except for days between 1st and 10th of a month.

### Controllers

#### Cluster upgrade executor

Thee will be a cluster that based on the `Cluster Upgrade` CRs will initiate the upgrades changing the labels on the specific CR(s), it could include Apps. 

This operator can also check on the `Upgrade Policy` if the cluster can be done or not, and in case it cannot happen alert or set an appropriate status on the object status.

#### Cluster upgrade scheduler

Ideally to automate the whole process there will be an operator that creates all the `Cluster Upgrade` CRs when a new release of Giant Swarm is created.

#### Existing CAPI controllers

There was [a proposal in CAPI upstream](https://github.com/kubernetes-sigs/cluster-api/blob/master/docs/proposals/20191017-kubeadm-based-control-plane.md) for the KubeadmControlPlane (later included in CAPZ components) to add `upgradeAfter` parameter to influence on the upgrades. The idea would be to create a new proposal that allows to point a new entity (`UpgradePolicy`) to extend the possibilities more than a single timestamp. Later controllers could leverage on that to allow changes or not to their reconciled resources.

## Open questions

- Do we scheduled automatic upgrades by default? or we let customer to scheduled them (maybe suggesting in our UI a cluster upgrade need to be scheduled)? 

- Do we setup a default upgrade policy for cluster that does not have one defined/attached?

- If we let customer to freeze the cluster we can apply for all type of upgrades? at some point it can be used for chart operator (or a new app upgrade operator) too to disable app upgrades?

## Additional actions

- Adapt our monitoring to not trigger false positive during upgrades. Right now, the upgrades usually trigger alerts (like `ServiceLevelBurnRateTooHigh`) which are false positives (all nodes are rolled during upgrade, so it should be omitted). At the same time having specific alerts for upgrades can be valuable (like one when master is not coming up after X minutes)

## Out of scope

- Check health of the cluster previous the upgrade is triggered.

- Perform automatic rollbacks when something goes wrong.
