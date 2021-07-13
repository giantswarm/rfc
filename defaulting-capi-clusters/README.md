# Defaulting of CAPI clusters with webhooks

This RFC describes a pattern for defaulting of CAPI clusters by utilizing Kubernetes webhooks extensively.

## Problem statement

We want clusters to be created with defaulted values.
These values should match the clusters in our [current product reasonably well](https://intranet.giantswarm.io/docs/product/pdr/006_capi-product-guidelines-values/).
Therefore we will need to default some values differently from upstream Cluster-API.

We do not expect to have full control of the method of cluster creation in the future.
Therefore we have to account for different methods of cluster creation ( e.g. kubectl, kubectl-gs, happa, gitops, ...) while keeping defaulting consistent between those methods.

## Defaulting with webhooks

Using mutating webhooks allows us to centralize the defaulting logic into webhooks.
Simplified clients can then rely on defaulted responses from the Kubernetes API by utilizing the server side dry-run feature.

The centralized defaulting logic additionally enables us to have no hardcoded values in any clients.

### Simple defaulting flow

We initially want to have a very simple defaulting flow which allows us to create Kubernetes clusters reliably.
The cluster creation is focused on kubectl-gs without excluding any other tooling to be used.

This is a high level overview of the cluster creation flow until the Custom Resources are applied:
1. `User` triggers cluster templating with `kubectl-gs template cluster`
2. `kubectl-gs` fetches upstream CAPI templates
3. `kubectl-gs` **removes** values from CAPI templates which we want to default differently
4. `kubectl-gs` returns minimal templates
5. `User` either `kubectl apply`s minimal templates or runs `dry-run`
6. `Admission Webhooks` default all missing values

From this overview we can deduct a set requirements for our admission webhooks:
- Webhooks must not have any side-effects (e.g. no additional objects are created or deleted)
- Webhooks must be able to fully default a Custom Resource without context of other Custom Resources in the request (e.g. a `MachineDeployment` must be fully defaulted even if the `Cluster` CR is not known)
- Webhooks must be able to determine which default values apply to the individual installation
- `kubectl-gs` must be able to remove values from the CAPI templates efficiently

### Source of truth for default values

Defining the source of truth for default values will be hard in the future with different CAPI versions and other needs for configurability.
We want to iterate faster at first and therefore a simple source of truth which might be inflexible is needed.
Versioning of configuration as releases for cluster upgrades is out of scope for this initial iteration.

Webhooks can utilize the already existing configuration options through `config-controller` to have access to global and installation specific defaults.
It will be necessary to package webhooks (such as `Kyverno policies`) as apps which have their configuration managed through the [config](https://github.com/giantswarm/config) repository.

The workflow for a developer to add a new default configuration is then the following:
1. `Developer` adds logic to new defaulting (e.g. a `kyverno policy`).
2. `Developer` adds templating to the app (e.g. [kyverno policies for aws](https://github.com/giantswarm/kyverno-policies/blob/main/helm/policies-aws/values.yaml) with local defaults in `values.yaml`.
3. `Developer` adds global and installation specific defaults through the [config](https://github.com/giantswarm/config) repository.

The workflow for a developer to then update update the default configuration is simple:
1. `Developer` updates configuration through the [config](https://github.com/giantswarm/config) repository.
2. `Developer` tags the `config` repository.
3. `Automation` rolls out the new config across installations.
