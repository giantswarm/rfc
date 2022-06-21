# Managed CRDs

## Table of Contents

- [Summary](#summary)
- [Motivation](#motivation)
- [Proposal](#proposal)

## Summary

As the Giant Swarm product is evolving, we are seeing an increasing number of use cases where we would benefit from more advanced management of CustomResourceDefinitions. This is especially the case with CRDs not developed by Giant Swarm (e.g. Cluster API, Prometheus and other open source projects), where we are frequently hitting issues regarding CRD updates.

The goal of this RFC is to provide a specification for a higher level API for managing CRDs (a set of CRDs and controllers) in a more holistic and, hopefully, ubiquitous way, easily adopted by any team.

## Motivation

The CRDs are very rarely deployed on their own. They are almost always accompanied with webhook configurations, which then also need a Service and a Certificate. The Service has to route requests to a correct port from the webhook Deployment, and the Deployment needs to mount correct Secret for the Certificate.

Deploying and upgrading all these objects separately and manually is error prone, and sometimes additional actions are required after the upgrade, especially when adding and/or removing CustomResourceDefinitions versions. All in all, there are multiple objects involved, and they are all connected in some way.

Currently we are generating CRDs in multiple ways, including, but not limited to:
- In apiextensions with `make generate-manifests` CLI command,
- In app repos with kustomize, by using upstream CRDs as the source and then applying transformations.
- Manually, by copying manifests from upstream projects.

We are then deploying those CRDs in multiple ways, including, but not limited to:
- With CLI command `opsctl ensure crds`,
- From app repos with crd-install template (a Job that applies CRDs from mounted ConfigMaps),
- From app repos as regular templates.

All these mentioned processes are error prone, we are frequently hitting different issues and people have questions around deploying and upgrading CRDs.

### Goals

- Provide higher level API for deploying CRDs and related objects (new CRDs and an operator reconciling them), so that developers do not work directly with `CustomResourceDefinition`, `ValidatingWebhookConfiguration`, `MutatingWebhookConfiguration`, `Service` and `Certificate`.
- New higher level CRDs have minimal API with defaults that follow best practices.
- New higher level CRDs are gitops friendly.
- A tool is provided to automatically generate new CRs (for new higher level CRDs) from existing `CustomResourceDefinition` and other related CRs.
- `CustomResourceDefinition` themselves can be stored anywhere, e.g. in a git repo or in a GitHub release asset.

### Non goals

- ...

## Proposal

TBA
