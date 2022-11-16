# Labelling workload cluster's apps

The purpose of this RFC is to propose a labelling scheme to safely identify a workload cluster's defining apps.

This is required for:

- deleting a workload cluster on CAPI;
- displaying a workload cluster's defining apps in Happa.

## Deleting a workload cluster on CAPI

To delete a workload cluster on CAPI we need to identify corresponding cluster app.

### Current state

On CAPI we are relying on the resource names (in the org namespace) for cluster app selection which is not recommended. There is no reference between cluster CR and cluster app CR - unlike other cluster's app resources, cluster app CR doesn't have `giantswarm.io/cluster` label. It cannot be set at the moment, since it will break cluster deletion.

### Proposal

Require `giantswarm.io/cluster` to be present in all app resources related to a workload cluster, including cluster app.

Introduce a new `giantswarm.io/cluster-app` label to safly mark cluster app CRs.

Refactor places where it's assumed that cluster app doesn't have `giantswarm.io/cluster` label to rely on a new `giantswarm.io/cluster-app` label instead.

## Displaying a workload cluster's defining apps in Happa

In Happa, we display workload cluster's apps in two separate lists - apps installed by a user and default (preinstalled) apps. To achieve that, we need:

- fetch all App CRs related to a workload cluster. On CAPI this list should not contain cluster app App CR.
- split the App CRs into default apps and user installed apps.

### Current state

There is a `giantswarm.io/cluster` label that potentially can be used to address App CRs related to a workload cluster, but:

- it's missing in some App CRs on vintage (currently we fetch all App CRs in a cluster namespace);
- it's missing in a cluster app on CAPI (currently we use `giantswarm.io/cluster` label to select cluster's App CRs in the organization namespace).

There is no suitable way to distinguish apps installed by a user from default apps.

### Proposal

#### For cluster's apps fetching:

On vintage, let's make `giantswarm.io/cluster` label to be required for all app resources related to a workload cluster.

On CAPI, proposal from the "Deleting a workload cluster on CAPI" will also suit this use case. We will fetch all cluster's app resources relying on the `giantswarm.io/cluster` label and the `giantswarm.io/cluster-app` label can be used to filter out cluster app from a list.

#### For splitting cluster's apps into two lists:

We could eather introduce a new label to mark default apps bundle e.g. `giantswarm.io/installed-by-default`, or we can set `giantswarm.io/managed-by` label of a default apps bundle to something specific (right now it's not set).

Require that `giantswarm.io/managed-by` label is correctly set for app bundle's child apps. It should point to a parent app.
