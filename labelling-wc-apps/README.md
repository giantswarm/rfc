# Labelling workload cluster's apps

The purpose of this RFC is to propose a labelling scheme to safely identify a workload cluster's defining apps.

This is required for:

- deleting a workload cluster on CAPI;
- displaying a workload cluster's defining apps in a client like the web UI (happa).

## Deleting a workload cluster on CAPI

To delete a workload cluster on CAPI, we need to identify the corresponding cluster app.

### Current state

On CAPI we are relying on the resource names (in the org namespace) for cluster app selection which is not recommended. There is no reference between cluster CR and cluster app CR - unlike other cluster's app resources, cluster app CR doesn't have `giantswarm.io/cluster` label. It cannot be set at the moment, since it will break cluster deletion.

### Proposal

Require the `giantswarm.io/cluster` label to be present in all App resources related to a workload cluster, including the cluster app.

Introduce a new `application.giantswarm.io/cluster-app` label to safely mark cluster app resources (the App CR).

Refactor places where it's assumed that cluster app doesn't have `giantswarm.io/cluster` label to rely on a new `application.giantswarm.io/cluster-app` label instead.

## Displaying a workload cluster's defining apps in Happa

In Happa, we intend to display a workload cluster's apps in two separate lists - apps installed by a user and default (preinstalled) apps. To achieve that, we need:

- fetch all App CRs related to a workload cluster. Currently we don't display cluster app in Happa, so we should either fetch all the apps except cluster app, or we need a way to filter it out later.
- split the App CRs into default apps and user installed apps.

### Current state

There is a `giantswarm.io/cluster` label that potentially can be used to address App CRs related to a workload cluster, but:

- it's missing in some App CRs on vintage (currently we fetch all App CRs in a cluster namespace);
- it's missing in a cluster app on CAPI (currently we use `giantswarm.io/cluster` label to select cluster's App CRs in the organization namespace).

There is no suitable way to distinguish apps installed by a user from default apps.

For app bundles, we rely on the fact that a child app should have `giantswarm.io/managed-by` label that points to its parent app. This is not a solid criteria because the `giantswarm.io/managed-by` label can express other meanings as well.

### Proposal

#### For cluster's apps fetching:

On vintage, let's make `giantswarm.io/cluster` label to be required for all app resources related to a workload cluster.

On CAPI, proposal from the "Deleting a workload cluster on CAPI" will also suit this use case. We will fetch all cluster's app resources relying on the `giantswarm.io/cluster` label and the `application.giantswarm.io/cluster-app` label can be used to filter out cluster app from a list.

#### For splitting cluster's apps into two lists:

We could either introduce a new label to mark default apps bundle, e.g. `application.giantswarm.io/installed-by-default`, or we can set the `giantswarm.io/managed-by` label of a default apps bundle to something specific (right now it's not set).

To determine a connection between an app bundle and it's child apps let's introduce a new label that should be specifically set for child apps and point to the parent app, e.g. `application.giantswarm.io/parent-app`.

## Summary

Require `giantswarm.io/cluster` label for all App CRs related to a workload cluster, both on vintage and on CAPI (including cluster app).

Introduce a new `application.giantswarm.io/cluster-app` label to mark cluster app App CRs.

Introduce a new `application.giantswarm.io/installed-by-default` label to mark default app bundle App CRs, or we can set the `giantswarm.io/managed-by` label of a default apps bundle App CRs to something specific.

Introduce a new `application.giantswarm.io/parent-app` label that should be specifically set for child apps of an app bundle and point to the parent app.
