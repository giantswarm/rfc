# Merging config in a gitops context

Our app platform utilizes configmaps / secrets heavily to pass configuration into apps.

*The following RFC will focus on configmaps but the same problem and solution is also applicable for secrets!*

These configmaps are often either shared between multiple instances of the same app or have shared values between apps.
In gitops the intended solution for both of these cases is to use `bases` and `overwrites` which is achieved through `kustomize`.

## Problem Statement

The content of a configmap is a list of key-value pairs.
Therefor configuration (especially nested configuration) is usually grouped under a single key (e.g. `values.yaml`).

It is currently not possible to merge any `overwrite` into a configmap key because the associated value is **always** treated as a string.

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
The only way to overwrite would be to overwrite the entire content of the `values` key.

## Context

We ran into this issue hard when we made cluster-API releases more DRY by using bases.
All parts of our setup currently rely on `app` CRs and their configuration through configmaps.

Full context of the PR can be found here: https://github.com/giantswarm/workload-clusters-fleet/pull/130

## Solution Proposal

Our app platform offers a layerd configuration approach already which we can utilize to enable us here.

An app CR has two fields where configuration can be supplied:
```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
metadata:
  name: something
  namespace: org-some
spec:
  config:
    configMap:
      name: flux01-default-apps-config
      namespace: org-some
  userConfig:
    configMap:
      name: flux01-userconfig
      namespace: org-some
```
The functionality means that values in `config` will be overlayed by values from `userconfig`.
So far we only used this functionality to supply Giant Swarm offered configuration through `config` and encouraged end users to only use the `userconfig` field.

The proposal is to use `config` for cases in gitops where we can not merge configmaps through `kustomize`.
From preliminary testing this works without any issues **but** is a change to how we treated this feature so far in the app platform.

### Pros
- Easy to just use
- Easy to explain to customers
### Cons
- Change in the intended design in app platform
- Only sidestepping the issue, not really resolving it
- Only one layer of overwrites possible
