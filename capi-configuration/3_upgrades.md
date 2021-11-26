# Handling workload cluster upgrades

## Problem Statement

We want to ...
1. Make all changes transparent for the user before application
2. Continue supporting the immediate upgrade of clusters by pressing a single button / writing a single command
3. Continue supporting a scheduled upgrade of a cluster
4. Integrate the process into the proposed gitops-management
5. Utilize the managed-configmap approach to ensure clusters adhere to the definition in their release at all times
6. Ensure that an upgrade to a cluster is decoupled from upgrades of other components
7. Allow easy integration into other pipelines and formats users might want to utilize for cluster management.
8. Have a single source of truth for the definition of an upgrade action

## Triggering an Upgrade

Our current method to trigger an upgrade is to change the release-version label on the `Cluster` resource. This can be done by GS staff, customers and automation through various interfaces.
This change will trigger the actual upgrade by letting a newer set of components manage the cluster.
However, when introducing the [new structure for releases](0_capi-releases), this process will be different. The release will no longer be tied to the components.
Instead, each release version will relate to a set of configmaps, defining the defaults and basic structure for the cluster resources.
So, triggering an upgrade in the future will mean to request the change of certain values within the CR itself. This is a breaking change since changing the release version label alone will no longer trigger an upgrade.
The reason for this is that we want to support a gitops-centered management of the cluster lifecycle.
Changes to the Cluster resources should ideally not be triggered inside kubernetes, but inside the source repository. (However, we want to continue to support cluster management without gitops)

## Defining the Upgrade

We established that upgrading the cluster `x` to version `y` means that the cluster resources of `x` have to be mutated so that they adhere to the structure defined in the release `y` configmaps.
In order to make this possible, the mutating component needs to know the difference between cluster `x` and a cluster with the same configuration in version `y`.
One easy way to get this information is to make a `dry-run` request to the management API to create such a cluster.
The proposed changes can then be expressed as a `diff` between the two clusters or just as the mutated cluster resources themselves.

## Client

This mechanism can easily be implemented in `kubectl-gs` since we already use the `dry-run` for CAPI cluster creation.
It seems straight-forward to add functionality to handle upgrades as well.
Input would be the cluster and desired version and output would be the `diff`.

## Upgrade Mechanism

In order to support different use-cases, we simply need different formats for the `diff` described above.
By adding a flag, the command could give us an output that can be [committed to a git repository](2_gitops-management) directly.
Another one could give us the cluster resources to apply the changes through the management API. 
In order to support scheduled upgrades we can add an output format that includes the upgrade time and can be picked up and applied later by an operator.
We can also add an `--apply` flag that will immediately apply the upgrade (schedule) action to the management custer or create a PR via automation.

## Mutable Fields

With the approach described above, we need to be aware of how specific fields should be treated during an upgrade.
If an empty field has a default value in the new version, it should be defaulted to this value.
If a populated field has a default value in the new version, we can either overwrite it or leave it unchanged.
In order to determine which fields are mutable and should be overwritten during an upgrade, the definition of mutable fields has to be part of the release definition itself or a separate upgrade definition.
When calculating the `diff`, this definition has to be taken into account.

## Example workflow

![Example](upgrade.gif)

See slides [here](https://docs.google.com/presentation/d/1_ImURpdO3T8HxyBNraTsoAiPJy6ZEidgEE7s_8i86K0/edit?usp=sharing).

Miro: https://miro.com/app/board/uXjVOfw7Hpw=/?invite_link_id=175751241840

## Open Questions

- Will customers give us git access?
- When operators are upgraded continuously, how often will CR-based upgrades be needed? Mainly for kubernetes upgrades?
- Should something like kubernetes version be managed through customers github?
- What if operator upgrades demand CR upgrades but customers don't upgrade?
- How can we push customers to upgrade? (especially in gitops-scenario)

## Further Ideas

- If possible, `happa` should have the same functionality as `kubectl-gs`. If integration with gitops is not possible, it could be `read-only` mode for gitops-managed clusters.
- The scheduled upgrades should evolve towards [automated upgrades](https://github.com/giantswarm/rfc/tree/main/automatic-cluster-upgrades) to keep customers up-to-date at all times.