---
creation_date: 2024-02-12
issues:
- https://github.com/giantswarm/giantswarm/issues/29790
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
- https://github.com/orgs/giantswarm/teams/team-phoenix
- https://github.com/orgs/giantswarm/teams/team-rocket
state: review
summary: Giant Swarm cluster providers should use a consistent naming scheme across all platforms.
---

# Standardisation of provider naming scheme

## Current situation

Depending on the provider, we use a different naming scheme. Our current provider names are:

- CAPA
- CAPZ
- cloud-director
- gcp
- openstack
- vsphere

For CAPA/CAPZ, this is currently unavoidable as the aws/azure names refer to our vintage providers. However, this blocker is removed once all vintage clusters have been migrated to CAPI.

Having this split in naming conventions causes some confusion, and whilst this is relatively minor it makes sense to pick a specific scheme (especially before adding any more providers). There appears to be no documented reason for choosing either scheme (aside from the aforementioned collision with our vintage providers) - this RFC aims to address that.

Note: a _platform_ as used in this document can be thought of as a _location_ (e.g. I deployed on AWS). Whereas a _provider_ is the mechanism used to deploy (e.g. I deployed on AWS using CAPA).

## Moving forward

There are two options moving forward. One is to use the CAPx acronym, and the other is to use the platform name.

### CAPx

Pros:

- Caters for multiple providers per platform (e.g. CAPA and EKS clusters on AWS).
- More uniform than platform names.
- Widely used and understood in the Kubernetes industry.
- Unique and unambiguous.

Cons:

- Not as descriptive and harder to grok at a glance.

### Platform name

Pros:

- Descriptive and easy to understand.

Cons:

- Creates a 1:1 mapping between provider and plaform (see CAPA vs EKS above).

## Outcome

I would suggest that given the possibility of having multiple providers for a single platform, we should rename gcp/vcd/vsphere/openstack in order to align with the CAPx naming scheme.

### Changes

- CAPA (no change)
- CAPZ (no change)
- cloud-director > CAPVCD
- gcp > CAPG
- openstack > CAPO
- vsphere > CAPV

Achieving this will require changes in at least the following places:

- configuration (config repo, flux etc)
- repo names
- operators which use provider names as logic