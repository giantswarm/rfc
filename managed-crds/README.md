# Managed CRDs

## Table of Contents

- [Managed CRDs](#managed-crds)
  - [Table of Contents](#table-of-contents)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non goals / Future work](#non-goals--future-work)
  - [Proposal](#proposal)
    - [User stories](#user-stories)
    - [API Implementation Details/Notes/Constraints](#api-implementation-detailsnotesconstraints)
      - [*`CustomResourceDefinitionGroupDeployment`*](#customresourcedefinitiongroupdeployment)
      - [*`CustomResourceDefinitionDeployment`*](#customresourcedefinitiondeployment)
      - [*`ConversionWebhookTemplate`*](#conversionwebhooktemplate)
      - [*`MutatingWebhookTemplate`*](#mutatingwebhooktemplate)
      - [*`ValidatingWebhookTemplate`*](#validatingwebhooktemplate)
      - [*`ServiceCertificateTemplate`*](#servicecertificatetemplate)
      - [Common structures](#common-structures)
    - [Installing CRDs](#installing-crds)
    - [Upgrading CRDs](#upgrading-crds)
      - [Adding API version to CustomResourceDefinition](#adding-api-version-to-customresourcedefinition)
      - [Removing API version from CustomResourceDefinition](#removing-api-version-from-customresourcedefinition)
    - [Deleting CRDs](#deleting-crds)

## Summary

As the Giant Swarm product is evolving, we are seeing an increasing number of use cases where we would benefit from more advanced management of `CustomResourceDefinitions`. This is especially the case with CRDs not developed by Giant Swarm (e.g. Cluster API, Prometheus and other open source projects), where we are frequently hitting issues regarding CRD updates.

The goal of this RFC is to provide a specification for a higher level API for managing CRDs (a set of CRDs and controllers) in a more holistic and, hopefully, ubiquitous way, easily adopted by any team.

## Motivation

The CRDs are very rarely deployed on their own. They are almost always accompanied with webhook configurations, which then also need a `Service` and a `Certificate`. The `Service` has to route requests to a correct port from the webhook `Deployment`, and the `Deployment` needs to mount correct `Secret` for the `Certificate`.

Deploying and upgrading all these objects separately and manually is error prone, and sometimes additional actions are required after the upgrade, especially when adding and/or removing `CustomResourceDefinitions` versions.

All in all, there are multiple objects involved, they are all connected in some way, and updating some of them often entails additional work where some other objects also have to be correctly and consistently updated as well, or some additional operations have to be performed.

Currently we are generating CRDs in multiple ways, including, but not limited to:
- In apiextensions with `make generate-manifests` CLI command,
- In app repos with kustomize, by using third party CRDs as the source and then applying transformations.
- With bash scripts.
- Manually, by copying manifests from third party projects.

We are then deploying those CRDs in multiple ways, including, but not limited to:
- With CLI command `opsctl ensure crds`,
- From app repos with crd-install template (a Job that applies CRDs from mounted ConfigMaps),
- From app repos as regular templates.

All these mentioned processes are error prone, we are frequently hitting different issues and people have questions around deploying and upgrading CRDs.

### Goals

- Provide higher level API for deploying CRDs and related objects. This higher level API is a set of new CRDs (and an operator reconciling them).
- New API is used instead of directly using `CustomResourceDefinition`.
- New API is used instead of directly using `ValidatingWebhookConfiguration`.
- New API is used instead of directly using `MutatingWebhookConfiguration`.
- New API is used instead of directly using webhook `Service`.
- New API is used instead of directly using webhook `Certificate`.
- New API can specify which webhook `Deployment` has to be updated with correct webhook-related fields, e.g. set correct Volume with Certificate Secret mounted.
- New higher level CRDs have minimal API with defaults that follow best practices.
- New API is gitops friendly, e.g. it does not use `Spec` for fields that should be in `Status` (e.g. fields that are automatically updated by the operator).
- A tool is provided to automatically generate new API CRs from existing `CustomResourceDefinition` and other related CRs.
- New API has support for installing CRDs from any web location with a URL (e.g. GitHub release asset), or from a git repo (plain CRDs or Helm/kustomize files that produce CRDs).

### Non goals / Future work

- Define where `CustomResourceDefinition` resources themselves can be stored.

## Proposal

### User stories

TBA

### API Implementation Details/Notes/Constraints

This RFC introduces new higher level API for managing CRDs and other related objects. The new API includes the following CRDs:

- `CustomResourceDefinitionGroupDeployment` for managing a set of CRDs from the same API group, with same set of API versions, and with common webhook configurations (including webhook Service and Certificate, as well managing all required fields in the webhook's Deployment).
- `CustomResourceDefinitionDeployment` for managing a single CRD and its webhook configuration (including webhook Service and Certificate, as well managing all required fields in the webhook's Deployment).
- `ConversionWebhookTemplate` for defining a conversion webhook for a single CRD, or for a set of CRDs that have the same conversion webhook configuration.
- `MutatingWebhookTemplate` for defining a mutating webhook configuration for a single CRD, or for a set of CRDs that share the same mutating webhook configuration.
- `ValidatingWebhookTemplate` for defining a validating webhook configuration for a single CRD, or for a set of CRDs that share the same validating webhook configuration.
- `ServiceCertificateTemplate` for defining a template for the `Certificate` that is used for the webhook `Service` for a single CRD, or for a set of CRDs.

The following sections define the API of these CRDs. The CRDs are ordered in kind of top-down fashion, starting from the highest level all-encompassing CRD group deployment and finishing with templates for other CRD-related resources.

#### *`CustomResourceDefinitionGroupDeployment`*

TBA

Example:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: CustomResourceDefinitionGroupDeployment
metadata:
  name: cluster-api-core
spec:
  group: cluster.x-k8s.io
  versions:
    storage: v1beta1
    served:
      - name: v1alpha4
      - name: v1alpha3
        deprecated: true
  kinds:
  - Cluster
  - Machine
  - MachineSet
  - MachineDeployment
  source:
    type: File
    url: https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.1.4/core-components.yaml
  webhooksConfig:
    mutatingWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: MutatingWebhookTemplate
        name: cluster-api-core
    validatingWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ValidatingWebhookTemplate
        name: cluster-api-core
    conversionWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ConversionWebhookTemplate
        name: cluster-api-core
    handler:
      service:
        namespace: giantswarm
        name: capi-webhook-service
    certificate:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ServiceCertificateTemplate
        name: capi
    deployment:
      name: capi-controller-manager
      mode: Update
```

#### *`CustomResourceDefinitionDeployment`*

TBA

Example:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: CustomResourceDefinitionDeployment
metadata:
  name: cluster-api-core-cluster
spec:
  group: cluster.x-k8s.io
  versions:
    storage: v1beta1
    served:
      - name: v1alpha4
      - name: v1alpha3
        deprecated: true
  kind: Cluster
  source:
    type: File
    url: https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.1.4/core-components.yaml
  webhooksConfig:
    mutatingWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: MutatingWebhookTemplate
        name: cluster-api-core-cluster
    validatingWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ValidatingWebhookTemplate
        name: cluster-api-core-cluster
    conversionWebhook:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ConversionWebhookTemplate
        name: cluster-api-core-cluster
    handler:
      service:
        namespace: giantswarm
        name: capi-webhook-service
    certificate:
      enabled: true
      templateRef:
        apiGroup: core.giantswarm.io/v1alpha1
        kind: ServiceCertificateTemplate
        name: capi
    deployment:
      name: capi-controller-manager
      mode: Update
```

#### *`ConversionWebhookTemplate`*

`ConversionWebhookTemplate` is a template for setting `CustomResourceDefinition`'s `Spec.Conversion` field.

The `ConversionWebhookTemplate` resource is referenced in a `CustomResourceDefinitionDeployment` or in a `CustomResourceDefinitionGroupDeployment`. The resource that references a `ConversionWebhookTemplate` must specify for which `CustomResourceDefinition` this `ConversionWebhookTemplate` is used.

```
type ConversionWebhookTemplate struct
```

- `Handler` (required)
  - Type: [`WebhookHandlerConfig`](#webhookhandlerconfig)
  - Description: Handler specifies what handles conversion requests.

Example 1:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: ConversionWebhookTemplate
metadata:
  name: cluster-api-core-cluster
spec:
  handler:
    service:
      namespace: giantswarm
      name: capi-webhook-service
```

Example 2:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: ConversionWebhookTemplate
metadata:
  name: some-resource-conversion
spec:
  handler:
    service:
      namespace: giantswarm
      name: some-webhook-service
      path: "/convert"
      port: 6443
```

#### *`MutatingWebhookTemplate`*

`MutatingWebhookTemplate` is a template for creating a webhook that is added to a `MutatingWebhookConfiguration`.

The `MutatingWebhookTemplate` resource is referenced in a `MutatingWebhookTemplate` or in a `CustomResourceDefinitionGroupDeployment`. The resource that references a `MutatingWebhookTemplate` must specify for which `CustomResourceDefinition` this `MutatingWebhookTemplate` is used.

The `MutatingWebhookTemplate` resource can optionally specify the webhook `Service`, otherwise the resource that references a `MutatingWebhookTemplate` must specify it.

Example 1:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: MutatingWebhookTemplate
metadata:
  name: cluster-api-core-cluster
spec:
  handler:
    service:
      namespace: giantswarm
      name: capi-webhook-service
      pathStyle: KubebuilderWebhookPathStyle
  objectSelector:
    matchLabels:
      cluster.x-k8s.io/watch-filter: capi
  reinvocationPolicy: IfNeeded
```

Example 2:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: MutatingWebhookTemplate
metadata:
  name: cluster-api-core-machine
spec:
  handler:
    service:
      namespace: giantswarm
      name: capi-webhook-service
      pathStyle: KubebuilderWebhookPathStyle
  objectSelector:
    matchLabels:
      cluster.x-k8s.io/watch-filter: capi
  ignoreErrors: true

```

#### *`ValidatingWebhookTemplate`*

`ValidatingWebhookTemplate` is a template for creating a webhook that is added to a `ValidatingWebhookConfiguration`.

The `ValidatingWebhookTemplate` resource is referenced in a `ValidatingWebhookTemplate` or in a `CustomResourceDefinitionGroupDeployment`. The resource that references a `ValidatingWebhookTemplate` must specify for which `CustomResourceDefinition` this `ValidatingWebhookTemplate` is used.

The `ValidatingWebhookTemplate` resource can optionally specify the webhook `Service`, otherwise the resource that references a `ValidatingWebhookTemplate` must specify it.

Example 1:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: ValidatingWebhookTemplate
metadata:
  name: cluster-api-core-cluster
spec:
  handler:
    service:
      namespace: giantswarm
      name: capi-webhook-service
      pathStyle: KubebuilderWebhookPathStyle
  objectSelector:
    matchLabels:
      cluster.x-k8s.io/watch-filter: capi
```

Example 2:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: ValidatingWebhookTemplate
metadata:
  name: cluster-api-core-machine
spec:
  handler:
    service:
      namespace: giantswarm
      name: capi-webhook-service
      pathStyle: KubebuilderWebhookPathStyle
  objectSelector:
    matchLabels:
      cluster.x-k8s.io/watch-filter: capi
  ignoreErrors: true
```

#### *`ServiceCertificateTemplate`*

`ServiceCertificateTemplate` is a template for a `Certificate` that is used by a `Service`.

The `ServiceCertificateTemplate` resource is referenced in a `CustomResourceDefinitionDeployment` or in a `CustomResourceDefinitionGroupDeployment`. The resource that references a `ServiceCertificateTemplate` must specify the name of the `Service` for which the `Certificate` will be used, so that reconciler can set required DNS names when creating the `Certificate`.

```
type ServiceCertificateTemplateSpec struct
```

- `secretName` [required]
  - Type: `string`
  - Description: Name of the secret where the certificate is stored.
- `IssuerRef`
  - Type: [`TypedLocalObjectReference`](https://pkg.go.dev/k8s.io/api/core/v1@v0.24.1#TypedLocalObjectReference)
  - Description: Reference to `Issuer` or `ClusterIssuer` resource.

Example:

```
apiVersion: core.giantswarm.io/v1alpha1
kind: ServiceCertificateTemplate
metadata:
  name: capi
spec:
  secretName: capi-webhook-service-cert
  issuerRef:
    apiGroup: cert-manager.io/v1
    kind: ClusterIssuer
    name: selfsigned-giantswarm

```

#### Common structures

<span id="webhookhandlerconfig">`WebhookHandlerConfig`</span>

```
type WebhookHandlerConfig struct
```

- `URL` (optional)
  - Type: `*string`
  - Description: URL gives the location of the webhook, in standard URL form (`scheme://host:port/path`). Exactly one of URL or Service must be specified.
- `Service` (optional)
  - Type: [`*ServiceReference`](#servicereference)
  - Description: Service is a reference to the service for this webhook. Either Service or URL must be specified.

<span id="servicereference">`ServiceReference`</span>

```
type ServiceReference struct
```

spec TBA

### Installing CRDs

This section explains the steps that crd-operator goes through in order to install a CustomResourceDefinition.

TBA

### Upgrading CRDs

This section explains the steps that crd-operator goes through in order to upgrade a CustomResourceDefinition.

TBA

#### Adding API version to CustomResourceDefinition

TBA

#### Removing API version from CustomResourceDefinition

TBA

### Deleting CRDs

This section explains the steps that crd-operator goes through in order to delete a CustomResourceDefinition.

TBA
