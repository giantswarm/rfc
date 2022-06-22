# Managed CRDs

## Table of Contents

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non goals / Future work](#non-goals--future-work)
- [Proposal](#proposal)
  - [User stories](#user-stories)
  - [Implementation Details/Notes/Constraints](#implementation-detailsnotes-constraints)
    - [ServiceCertificateTemplate](#servicecertificatetemplate)
    - [ConversionWebhookTemplate](#conversionwebhooktemplate)
    - [ValidatingWebhookTemplate](#validatingwebhooktemplate)
    - [MutatingWebhookTemplate](#mutatingwebhooktemplate)
    - [CustomResourceDefinitionDeployment](#customresourcedefinitiondeployment)
    - [CustomResourceDefinitionGroupDeployment](#customresourcedefinitiongroupdeployment)

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
- New higher level CRDs are used instead of directly using `CustomResourceDefinition`.
- New higher level CRDs are used instead of directly using `ValidatingWebhookConfiguration`.
- New higher level CRDs are used instead of directly using `MutatingWebhookConfiguration`.
- New higher level CRDs are used instead of directly using webhook `Service`.
- New higher level CRDs are used instead of directly using webhook `Certificate`.
- Controllers that reconcile new CRs modify webhook Deployment if necessary, in order to set correct Volume with Certificate Secret mounted.
- New higher level CRDs have minimal API with defaults that follow best practices.
- New higher level CRDs are gitops friendly.
- A tool is provided to automatically generate new CRs from existing `CustomResourceDefinition` and other related CRs.
- `CustomResourceDefinition` themselves can be stored anywhere, e.g. in a git repo or in a GitHub release asset.

### Non goals / Future work

- Fully manage the Deployment for the webhook. Currently many upstream projects (e.g. Cluster API) have webhook servers deployed in the same binary with controllers that reconcile the CRs, so there would be a non-trivial amount of work to decouple webhooks from controllers, if we wanted to do that.

## Proposal

### User stories

TBA

### Implementation Details/Notes/Constraints

This RFC introduces new higher level API for managing CRDs and other related objects. The new API includes the following CRDs:

- `CustomResourceDefinitionGroupDeployment` for managing a set of CRDs from the same API group, with same set of API versions, and with common webhook configurations (including webhook Service and Certificate, as well managing all required fields in the webhook's Deployment).
- `CustomResourceDefinitionDeployment` for managing a single CRD and its webhook configuration (including webhook Service and Certificate, as well managing all required fields in the webhook's Deployment).
- `MutatingWebhookTemplate` for defining a mutating webhook configuration for a single CRD, or for a set of CRDs that share the same mutating webhook configuration.
- `ValidatingWebhookTemplate` for defining a validating webhook configuration for a single CRD, or for a set of CRDs that share the same validating webhook configuration.
- `ConversionWebhookTemplate` for defining a conversion webhook for a single CRD, or for a set of CRDs that have the same conversion webhook configuration.
- `ServiceCertificateTemplate` for defining a `Certificate` template for a single CRD, or for a set of CRDs.

The following sections define the API of these CRDs. The CRDs are ordered in kind of bottom-up fashion, starting from templates and finishing with all-encompassing `CustomResourceDefinitionGroupDeployment`.

#### ServiceCertificateTemplate

TBA

#### ConversionWebhookTemplate

TBA

#### ValidatingWebhookTemplate

TBA

#### MutatingWebhookTemplate

TBA

#### CustomResourceDefinitionDeployment

TBA

#### CustomResourceDefinitionGroupDeployment

TBA
