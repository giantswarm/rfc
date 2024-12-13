---
creation_date: 2022-04-01
state: approved
---

# Merging config in a gitops context

Our app platform utilizes configmaps / secrets heavily to pass configuration into apps.

*The following RFC will focus on configmaps but the same problem and solution are also applicable for secrets!*

These configmaps are often either shared between multiple instances of the same app or have shared values between apps.
In gitops the [intended solution](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/#2-create-variants-using-overlays) for both of these cases is to use `bases` and `overlays` which is achieved through `kustomize`.

## Problem Statement

The `data` section of a configmap is a mapping of keys to values.
Therefore configuration (especially nested configuration) is usually grouped under a single key (e.g. `values`).

It is currently not possible to merge any `overlay` into a configmap key because the associated value is **always** treated as a string.

Example:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  labels:
    giantswarm.io/managed-by: flux
  name: flux01-config
  namespace: org-multi-project
data:
  values: |
    nodePools:
    - class: default
      failureDomain: gb-lon-1
      name: default
      replicas: 3
```
All fields under `values` will be grouped into a simple `string` even though they are valid `yaml`.
The only way to overlay would be to overlay the entire content of the `values` key.

## Context

This problem became most apparent while working to make Cluster API releases more DRY by using bases.
All parts of our setup currently rely on `app` CRs and their configuration through configmaps.

Full context of the PR can be found here: https://github.com/giantswarm/workload-clusters-fleet/pull/130

## Solution Proposal

Our app platform offers a layered configuration approach already which we can utilize to enable us here.

An app CR has three fields where configuration can be supplied, out of which two can be used for providing user
configuration:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
metadata:
  name: something
  namespace: org-some
spec:
  # config:
  #   configMap:
  #     name: mycluster-cluster-values
  #     namespace: org-some
  extraConfigs:
    - kind: configMap
      name: flux01-extra-config
      namespace: org-some
      # priority: 25 by default
  userConfig:
    configMap:
      name: flux01-userconfig
      namespace: org-some
```

**The `.spec.config` should be used with caution. It should either be set explicitly to the `<CLUSTER_NAME>-cluster-values`,
or should be left empty to be later populated by either `app-admission-controller`, upon submission, or `app-operator`, upon
reconciliation. Using this field to provide other values may result in the mis-configuration of certain apps.**

The values coming from these fields are merged based on their priority, see the [App Platform configuration](https://docs.giantswarm.io/tutorials/fleet-management/app-platform/app-configuration/#levels). Both, the `.spec.config` and `.spec.userConfig`,
fields get the fixed priorities, making their place in the hierarchy fixed as well, while the `.spec.extraConfigs` memebers
priorities are configurable.

The proposal is to use `.spec.extraConfig` for cases in GitOps where we can not merge configmaps through `kustomize`.
From preliminary testing this works without any issues **but** is a change to how we treated this feature so far in the app platform.

### Pros
- Easy to just use
- Easy to explain to customers
- Leave the `.spec.config` empty for controllers to populate
- Multiple layers of overlays possible

### Cons
- Only sidestepping the issue, not really resolving it in terms of GitOps.

## Future work

The ideal solution would be to support the desired usecase in `kustomize` directly.
The maintainers of `kustomize` have already stated that they would approve of [several proposals for this feature](https://github.com/kubernetes-sigs/kustomize/issues/3787).
Unfortunately the maintainers do not have the resources to handle the implementation currently, so we should check from our side if we can help in the future.
