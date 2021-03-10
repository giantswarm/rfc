# RFC 016 - CLUSTER API UPGRADES

## Reasoning

As part of the Cluster API (CAPI) Hive Sprint, the `upgrades hive` decided to create a document to gather all actions need to be done in order to upgrade a workload cluster successfully as well as bring the functionality we have already built to trigger the upgrades.

## Scope

This document covers only the action to upgrade the workload cluster without solving problems related to the versioning of the different CAPI controllers and/or deciding which controller reconciles a cluster.

At the same time all the automation on top of the upgrades, like freeze periods or maintainance windows, are out of the scope here ([include in RFC 0015](/0015-automatic-cluster--upgrades)).

## Context

The current approach to upgrade a workload cluster in CAPI world involves a series of steps described below:

- Ensure there is a `machine image` with the correct target Kubernetes version (contains kubelet and kubeadm). 
- Upgrade the control plane machines:
  - Generate a new infrastructure `MachineTemplate` resource (with new image ID if needed) and create it in the Management API.
  - Set the new Kubernetes version in `KubeadmControlPlane` resource.
  - Change the infrastructure `MachineTemplate` on the `KubeadmControlPlane` to the new one and apply the new version of `KubeadmControlPlane`.
- Upgrade machine pools (workers):
  - Modify the infrastructure `MachinePool` resource (with new image ID) if needed.
  - Set the new Kubernetes version in `MachinePool` resource.

Also our operators watch for changes on the Cluster CR's labels to trigger an upgrade. That functionality should be kept in the new operator we build.

## Open questions

- Do we need to change the reference of the image ID for every upgrade?
- For `MachinePool`, do we need to make the operation in a transactional way to avoid multiple upgrade (in case we need to change infrastructure and agnostic `MachinePool`)?
- Are the provider controllers aware of KCP upgrades and wait till they are done before start upgrading Machine Pools?
- Do we need to allow different strategics to define the sequence `MachinePool` resoures are upgraded?
