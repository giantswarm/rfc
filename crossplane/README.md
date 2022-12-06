# Crossplane MVP on Management Clusters

Managed Crossplane offering is under development as per customers' requests.
This document discusses all the required elements of Crossplane's deployment
and the design decisions we make along the way.

> 💡Please note: This document defines decisions made towards delivering
  Crossplane MVP to select customers on a deadline. It is not indicative of
  final plans for Crossplane on Giant Swarm Management Clusters.

## Crossplane building blocks

For ease of describing each proposal, we will divide a fully functional
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
`providers.pkg.crossplane.io` resource will cause Crossplane operators to
deploy provider operators and all necessary resources.

- Provider-specific Operator
- Provider-specific Custom Resource Definitions, usually
`*.<provider-name>.crossplane.io`
- Other Kubernetes resources

### Stage 3 - Provider Configuration

Just deploying Providers is not enough for them to be functional. They still
need to be configured with passwords, secrets, access keys, API keys, and the
like. Each Provider comes with its configuration CRD, usually
`providerconfigs.<provider-name>.crossplane.io`.

For example, the AWS provider will require a `ProviderConfig` similar to the
one below to be able to perform reconciliation. `crossplane-system/aws-creds`
The Secret should contain AWS Access Key.

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

#### 1.a Install Crossplane as part of the App collection

This is useful if we want to install Crossplane App on every Management Cluster
by default. The configuration will live in `giantswarm/config`. This still
allows us to change available settings and Providers per Cloud Provider and per
Management Cluster.

#### 1.b Install Crossplane as HelmRelease in management-clusters-fleet

This is useful if we want to limit Crossplane to be deployed on select
Management Clusters. Creating a single `HelmRelease` resource allows us to
easily set chart values.

#### Decision

(1.b) Crossplane MVP will be installed as part of `management-clusters-fleet`.

### 2. Handling configuration and secrets

#### 2.a Giant Swarm stores customer secrets

In this case, Giant Swarm is responsible for all three stages of deployment,
including Provider Configuration. This means we need to store sensitive data
(AWS Access Key, GCP Account Keyfile, Azure Service Principal Keys, etc.),
support their encryption and decryption, and deliver them to Management
Clusters.

#### 2.b Giant Swarm manages Crossplane, the customer provides the keys

In this case, Giant Swarm is responsible for stages one and two. Our goal is to
deliver Crossplane and a set of Providers. It is up to the customer to create a
`Secret` and `ProviderConfig`. The structure of both resources is simple and
well-documented. It also makes sense given how the `ProviderConfig` definition
varies, depending on the Provider.

#### Decision

(2.b) Customers will be required to provide the keys.

### 3. Providers

#### 3.a The list of Providers is pre-defined and immutable

We deploy a provider that best matches the Cloud Provider's infrastructure:
- AWS <https://github.com/crossplane-contrib/provider-aws>
- Azure <https://github.com/crossplane-contrib/provider-azure>
- CAPA <https://github.com/crossplane-contrib/provider-aws>?
- GCP <https://github.com/crossplane/provider-gc>
- KVM is not supported; obviously, it's the customers' infrastructure
- OpenStack TBD (<https://github.com/crossplane-contrib/provider-terraform>???)

No other providers are available, even upon request. The offering is "managed".

#### 3.b Customers can pick and choose from a well-defined list of vetted Providers

We offer a curated selection of [all Crossplane
providers](https://github.com/orgs/crossplane-contrib/repositories). Clients
are free to pick the ones they like for us to install. The offering is "managed".

#### 3.c Customers can request any Provider they like

Customers can select any of the Providers they like to have. It means
Giant Swarm tests and vets the Provider to be able to support the customer and
"manage" the deployment.

#### 3.d Customers can install any Provider they like

Customers are free to create and configure `Provider` resources however and
whenever they like. Only stage 1 is managed. Customers are responsible for
running Providers much like with ArgoCD and custom operators on Management
Clusters.

#### Decision

(3.a) We will start with a pre-defined and immutable list of Providers.

#### 4. OpenStack provider

To our best knowledge, there are no dedicated OpenStack Crossplane providers.

## Decision

TBD

2022-12-06 update: As per [Oli's announcement](https://gigantic.slack.com/archives/CNHMVT6LW/p1670335252163369), OpenStack/CAPO development is suspended.

### Next steps

TBD
