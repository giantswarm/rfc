# RFC 0015 - Automatic Cluster Upgrades

As a user, and also as KaaS team provider, I would like to have the clusters running in the latest version automatically, and not worry about CVEs or EOL of the cluster components.

As a user, I would like to define maintenance windows to ensure clusters are not upgraded outside of these hours.

As a user I would like to mark a cluster as frozen and block upgrades for certain period of time.

## Reasoning

Our customers need to plan every upgrade on their side and manage the upgrades for every GS version. At the same time, Cloud Native projects and Giant Swarm are releasing more versions every time. It provokes a lot of time preparing and executing these upgrades which is not usually given much value to any of the stakeholders. 

Giant Swarm designed a versioning schema (semver), which includes all components on the stack, to ensure idempotency and expose the level of impact that changes bring to the customer. Patches and Minor releases should have no impact on the customer workloads, which mean can be applied in the environments at any time. 

## Current state

Right now the automatic upgrades are carried by Solution Engineers agreeing with the customer on upgrade windows and environments selection. The idea is to automate all this behavior and information under a Kubernetes operator and Custom Resource(s).

The Solution engineer plan cluster upgrades based on cluster type (environment, team,...) and maintenance windows offered by the customers. The upgrade is just a change on the cluster version field on the cluster Custom Resource (CR).

## Technical aspects

### User workflow

- The user creates a cluster without any additional configuration. The default window upgrade is selected. The cluster is eligible for upgrades during that period.

- The user can define a tailored upgrade window for the cluster

- The user can freeze (automatic) upgrades for the new cluster

### Operator workflow

1. Giant Swarm runs in each management cluster an operator that watches releases. 

2. As part of the reconciliation loop, the operator checks if there is any cluster eligible for upgrade.
 - There is a new patch/minor version active available. 
 - There is clusters not in the latest version of a major release. 
 - The cluster(s) match the window upgrade criteria to be upgraded.
 - The cluster(s) are not being upgraded. 
 - The cluster(s) are not marked as frozen.

3. The operator bump the version for the given set of clusters.

## Open questions

- Do we enable automatic upgrades by default? and then customer need to mark cluster(s) as frozen 

- Do we setup a default upgrade window for cluster that does not have one defined/attached?

- If we let customer to freeze the cluster we can apply for all type of upgrades? at some point it can be used for chart operator (or a new app upgrade operator) too to disable app upgrades?

## Additional actions

- Adapt our monitoring to not trigger false positive during upgrades. Right now, the upgrades usually trigger alerts (like `ServiceLevelBurnRateTooHigh`) which are false positives (all nodes are rolled during upgrade, so it should be omitted). At the same time having specific alerts for upgrades can be valuable (like one when master is not coming up after X minutes)

## Out of scope

- Check health of the cluster previous the upgrade is triggered.

- Perform automatic rollbacks when something goes wrong.
