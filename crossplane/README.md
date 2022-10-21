# Crossplane on Management Clusters

Managed Crossplane offering is under development as per customers' requests.
This document discusses all the required elements of Crossplane's deployment
and design decisions we make along the way.

## Crossplane building blocks

For the ease of describing each proposal, we will divide a fully functional
Crossplane deployment into three stages.

### Stage 1 - Crossplane

The first stage is Crossplane itself. This is not enough to manage any
infrastructure yet.

- Crossplane Operator
- Crossplane RBAC Manager Operator
- Custom Resource Definitions:
  - `compositeresourcedefinitions.apiextensions.crossplane.io`
  - `compositionrevisions.apiextensions.crossplane.io`
  - `compositions.apiextensions.crossplane.io`
  - `configurationrevisions.pkg.crossplane.io`
  - `configurations.pkg.crossplane.io`
  - `controllerconfigs.pkg.crossplane.io`
  - `locks.pkg.crossplane.io`
  - `providerrevisions.pkg.crossplane.io`
  - `providers.pkg.crossplane.io`
  - `storeconfigs.secrets.crossplane.io`
- Other Kubernetes resources

### Stage 2 - Crossplane Providers

Infrastructure is managed by Providers. Creating a
`providers.pkg.crossplane.io` resource will cause Crossplane operator's to
deploy provider operators and all necessary resources.

- Provider-specific Operator
- Provider-specific Custom Resource Definitions, usually
`*.<provider-name>.crossplane.io`
- Other Kubernetes resources

### Stage 3 - Provider Configuration

Just deploying Providers is not enough for them to be functional. They still
need to be configured with passwords, secrets, access keys, API keys and the
like. Each Provider comes with their own configuration CRD, usually
`providerconfigs.<provider-name>.crossplane.io`.

For example, AWS provider will require a `ProviderConfig` similar to the one
below to be able to perform reconciliation. `crossplane-system/aws-creds`
Secret should contain AWS Access Key.

```yaml
apiVersion: aws.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: Secret
    secretRef:
      namespace: crossplane-system
      name: aws-creds
      key: creds
```

## Design proposals

### 1. Installation

#### Install Crossplane as part of App collection

This is useful if we want to install Crossplane App on every Management Cluster
by default. Configuration will live in `giantswarm/config`. This still allows
us to change available settings and Providers per Cloud Provider and per
Management Cluster.

#### Install Crossplane as HelmRelease in management-clusters-fleet

This is useful if we want to limit Crossplane to be deployed on select
Management Clusters. Creating a single `HelmRelease` resource allows us to
easily set chart values.

### 2. Handling configuration and secrets

#### Giant Swarm stores customer secrets

In this case, Giant Swarm is responsible for all three stages of deployment,
including Provider Configuration. This means we need to store sensitive data
(AWS Access Key, GCP Account Keyfile, Azure Service Principal Keys, etc.),
support their encryption and decryption, and deliver them to Management
Clusters.

#### Giant Swarm manages Crossplane, customer provides the keys

In this case, Giant Swarm is responsible for stages one and two. Our goal is to
deliver Crossplane and a set of Providers. It is up to the customer to create a
`Secret` and `ProviderConfig`. The structure of both resources is simple and
well documented. It also makes sense given how `ProviderConfig` definition
varies, depending on the Provider.

### 3. Providers

#### The list of Providers is pre-defined and immutable

#### Customers can pick and choose from a well defined list of vetted Providers

#### Customers can request any Provider they like

#### Customers can install any Provider they like

## Decision

### Next steps
