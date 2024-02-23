---
creation_date: 2021-09-17
issues:
- [https:/](https://github.com/giantswarm/giantswarm/issues/27420)
last_review_date: 2024-02-23
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
state: approved
summary: As part of the Cluster API hackathon the idea of how to automate the cluster upgrades allows us to brainstorm how it can be achieved taking into account customer requirements and technical limitations brought under the new upstream implementation.
---

# RFC 0015 - Automatic workload cluster upgrades

## Resources

- RFC [automatic app upgrades](../automatic-app-upgrades/README.md)

## User stories

- As a Giant Swarm customer, and also as a Giant Swarm maintainer, we would like to have workload clusters running in the latest version automatically, and not worry about patching security vulnerabilities or cluster components running out of updates (e. g. Kubernetes release end of life).

- As a customer admin, I would like to define upgrade windows, to ensure that upgrades happen when disruption is most suitable and impact on production traffic is minimal.

- As a customer admin, I would like to mark a workload cluster as "frozen" in order to block upgrades for a certain time period.

- As a customer admin, I want to define the upgrade order of clusters, so that certain workload clusters are upgraded to a distinct workload cluster release before others are.

- As a customer admin, I want to schedule an upgrade for a specific workload cluster to a certain day/time.

- As a customer, and also as Giant Swarm, we want to capture the result of an upgrade. Based on the result we can alert on a certain condition, track the history for certain cluster(s) or automate response based on the end state.

- As a customer, and also as Giant Swarm, we want to make the automatic upgrades compatible to GitOps, so the state of the infrastructure changes are tracked in Git.

## Reasoning

Our customers need to plan every upgrade on their side and manage the upgrades for every workload cluster release. Each customer has their own requirements regarding when they need to schedule upgrades (freeze periods, maintenance windows, etc.). At the same time, cloud native projects and Giant Swarm are continuously providing new releases. The preparation and execution of upgrades is time and labor intensive, while the fact that they are executed manually does not add much value to stakeholders.

Giant Swarm designed a versioning scheme (based on Semver), which includes all components on the stack, to ensure idempotence and expose the level of impact that changes bring to the customer. Patches and Minor releases should have no impact on the customer workloads, which means that they can be applied in the environments at any time.

## Current state

Right now the automatic upgrades are carried by Solution Engineers (AEs and SAs) agreeing with the customer on upgrade windows and environments selected. The idea is to automate all this behavior and information under a Kubernetes operator(s) and Custom Resource(s).

The Solution Engineer plans cluster upgrades based on cluster type (environment, team,...) and maintenance windows offered by the customers. The upgrade is just a change on cluster-<provider> App manifest of the cluster.

Based on the fact Giant Swarm is moving to Cluster API this is story let us define a new greenfield scenario where we can design a model that can be more generic and not focus only in Giant Swarm platform. The idea would be contribute as much as possible with upstream due the fact most of this functionality would be useful for everyone that manages clusters.

## Concepts

### Cluster upgrade entity

There are different reason why we are interested in having an object to define the upgrade intent.

- As we define in the user stories, we/customers would like to schedule upgrades on certain date from running version to a specific one. That way customer can plan upgrades ahead and so do we.

- We have a registry of upgrades done to a cluster for auditing and tracking purposes.

- We can save cluster upgrade status displaying if something goes wrong or not.

- In theory we can include apps upgrades together or separately. [UPDATE] Now [this is possible thanks to OCI registries and Flux](https://github.com/giantswarm/rfc/tree/main/automatic-app-upgrades).

### Maintenance schedule entity

Our customer can have a different set of constraints when it comes to allow changes in their clusters. The maintenance schedule would define those and then the clusters can rely on a policy to enforce the desired behavior.

The maintenance schedule would be reconciled by the cluster upgrade scheduler and it will program the upgrades based on that restrictions.

The maintenance schedule would contain

- A way to define dates or times where clusters (or relatives) can be modified.

- A way to define dates or times where clusters (or relatives) cannot be modified.

## Technical aspects

We envision aforementioned concepts would become custom resource definitions and there will be additional controllers that would enhance and ensure the correct behavior.

### Resources

#### ClusterUpgrade

Example resource:

```yaml
apiVersion:
kind: ClusterUpgrade
metadata:
  name: upgrade-to-cluster-openstack-v1.20
  namespace: default
spec:
  matchers:
  - name: cluster_id
    value: mgab6
    isRegex: false
  - name: dev_clusters
    key: stage
    value: dev
    isRegex: true
  releaseRef:
    apiVersion: application.giantswarm.io/v1alpha1
    kind: Release
    name: v1.20.0
  startTime: 2021-03-10T07:00:00Z
status:
  triggeredAt: 2021-03-10T10:00:00Z
  state: finished
  outcome: success
  finishedAt: 2021-03-10T10:31:10Z
  fromRelease: v1.16.0
  toRelease: v1.20.0
```

#### MaintenanceSchedule

Example resource:

```yaml
apiVersion:
kind: MaintenanceSchedule
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
```

This would allow upgrades to happen between 07:00 UTC and 17:00 UTC on Monday-Friday, except for days between 1st and 10th of a month.

### Controllers

#### Cluster upgrade executor

There will be an operator that based on the `Cluster Upgrade` CRs will trigger the upgrades changing the labels on the specific CR(s) when date matches or it will create the pull requests in Git repo to trigger the upgrade (Flux controllers could be used here for that).

This operator can also check on the `maintenance schedule` to verify the upgrade fulfil or not the criteria, and in case it does not, alert or set an appropriate status on the object status.

#### Cluster upgrade scheduler

Ideally to automate the whole process there will be an operator that creates all the `Cluster Upgrade` CRs when a new release of Giant Swarm is created (and/or possibly other events).

__Note__: Currently team Phoenix has developed a cluster upgrade operator that works with annotations for vintage product. So having their feedback here will be helpful.

## Open questions

- How Cluster Upgrade Scheduler knows there is a new version? Should the controller listen to cluster-<provider> releases? Can we use/extend Flux image reflector for that?

- Do we schedule automatic upgrades by default? Or do we let customer schedule them (maybe suggesting in our UI a cluster upgrade need to be scheduled)?

- Do we set up a default maintenance schedule for a cluster that does not have one defined/attached?

- If we allow a customer to freeze the cluster, can apply all types of upgrades? Can this mechanism also be used at some point by chart-operator (or a new app upgrade operator) to disable app upgrades?

## Additional actions

- Adapt our monitoring to not trigger false positives during upgrades. Right now, the upgrades usually trigger alerts (like `ServiceLevelBurnRateTooHigh`) which are false positives (all nodes are rolled during upgrade, so it should be omitted). At the same time having specific alerts for upgrades can be valuable (like one when master is not coming up after X minutes)

## Out of scope

- Check health of the cluster previous the upgrade is triggered.

- Perform automatic rollbacks when something goes wrong.
