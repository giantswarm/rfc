# Handling workload cluster upgrades

## Problem Statement

We want to ...
1. Make all changes transparent for the user before application
2. Continue supporting the current workflow of upgrading a cluster (Through GS staff, customers and automation)
3. Integrate the process into the proposed gitops-management
4. Utilize the managed-configmap approach to ensure clusters adhere to the definition in their release at all times
5. Ensure that an upgrade to a cluster is decoupled from upgrades of other components
6. Allow easy integration into other pipelines and formats users might want to utilize for cluster management.

## Triggering an Upgrade

Our current method to trigger an upgrade is to change the release-version label on the `Cluster` resource.
This can be done by GS staff, customers and automation through various interfaces. In this proposal we want to stick to this trigger method.
In our current product, this change will trigger the actual upgrade by letting a newer set of components manage the cluster.
However, when introducing the [new structure for releases](0_capi-releases) this will change. The release will no longer be tied to the components.
Instead, each release version will relate to a set of configmaps, defining the defaults and basic structure for the cluster resources.

## Upgrade Mechanism

Once the upgrade has been triggered, a component on the management cluster will have to make changes to the cluster resources so that it adheres to the structure defined in the release configmaps.
In this proposal we give this role to `kyverno`. Because the upgrade would be applied as an admission webhook, we would be able to review the changes using `dry-run` before actually applying them. This would also give us the chance to apply them not directly via management-API but by [creating a commit to a git repository](2_gitops-management).

## Client

We use `kubectl-gs template` to create templates for cluster creation. It seems straight-forward to add functionality to trigger upgrades as well.
This should include the ability to review changes, apply the upgrade directly by updating the version-label (This would guarantee backwards compatability) and creating commits to git repositories used for cluster management.

## Example workflow

![Example](upgrade.gif)

See slides [here](https://docs.google.com/presentation/d/1_ImURpdO3T8HxyBNraTsoAiPJy6ZEidgEE7s_8i86K0/edit?usp=sharing).

## Open Questions

- How can we simplify this procedure?
- How does this integrate with `happa`?
- ?