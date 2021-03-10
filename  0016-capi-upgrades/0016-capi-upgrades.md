# RFC 016 - CLUSTER API UPGRADES

## Reasoning

As part of the Cluster API (CAPI) Hive Sprint, the `upgrades hive` decided to create a document to gather all actions need to be done in order to upgrade a workload cluster successfully as well as bring the functionality we have already built to trigger the upgrades.

## Scope

This document only cover the action to upgrade the workload cluster without solving problems of versioning of the different CAPI controllers and/or deciding which controller reconcile a cluster.

At the same time all the automation on top of the upgrades, like freeze periods or maintainance windows, are out of the scope here ([include in RFC 0015](/0015-automatic-cluster--upgrades)).

Furthermore, a workload cluster can be upgraded in different ways:

- Apps installed in the cluster are upgraded (out of scope here). We have other non-CAPI components that already take care of that, like app-operator

- Cluster is reconciled by a newer CAPI controller. We may want to upgrade the Cluster to a newer CAPI controller release, which may change the infrastructure created to support the cluster (network, load balancers, etc). We do this update just changing the CAPI label on the Cluster CR, and we don't need a new machine image to be created/referenced by the CR's.

- Machine image used by control plane or workers is updated with new k8s version or new OS version. We may want to update the k8s version or the OS version running in the machines. In both cases, we need a new machine image using the updated components, and reference that image from the CR's.

## Context

The current approach to upgrade a workload cluster in CAPI world involves a series of steps described below:

- Ensure there is a `machine image` with the correct target Kubernetes version (contains kubelet and kubeadm). 
- Upgrade the control plane machines:
  - Generate a new infrastructure `MachineTemplate` resource (with new image ID if needed) and create it in the Management API.
  - Set the new Kubernetes version in `KubeadmControlPlane` resource.
  - Change the infrastructure `MachineTemplate` on the `KubeadmControlPlane` to the new one and apply the new version of `KubeadmControlPlane`.
- Upgrade machine pools. As default, we walk through all existing machine pools one by one:
  - Make sure there are no MachinePools being already upgraded.
  - Modify the infrastructure `MachinePool` resource (with new image ID) if needed.
  - Set the new Kubernetes version in `MachinePool` resource.

Also our operators watch for changes on the Cluster CR's labels to trigger an upgrade. That functionality should be kept in the new operator we build.

## Open questions

- Do we need to change the reference of the image ID for every upgrade?
No there will be upgrades that only change a cluster CR field/version but does not require a new image.

- For `MachinePool`, do we need to make the operation in a transactional way to avoid multiple upgrade (in case we need to change infrastructure and agnostic `MachinePool`)?
No, there is no a use case where two resources has to be modified at same time. But the changes done to the `MachinePool` must be done all at once (obviously :)).

- Are the provider controllers aware of KCP upgrades and wait till they are done before start upgrading Machine Pools?
There could be provider controllers that check version of control plane before upgrading `MachinePools` but we are not relying on it and the operator we will implement will take care of the correct sequence.

- Do we need to allow different strategics to define the sequence `MachinePool` resoures are upgraded?
Yes we think it would a case to be able set preferences between `MachinePools` so ones are upgraded before others or customer can set cooldown periods between rolls. By default we are implementing a sequential upgrade fashion starting with control plane and moving to `MachinePools` one by one ordered alphabetically (leaving 15 minutes between rolls). 
