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
- CAPG
- CAPZ
- cloud-director
- openstack
- vsphere

For CAPA/CAPZ, this is currently unavoidable as the aws/azure names refer to our vintage providers. However, this blocker is removed once all vintage clusters have been migrated to CAPI.

Having this split in naming conventions causes some confusion, and whilst this is relatively minor it makes sense to pick a specific scheme (especially before adding any more providers). There appears to be no documented reason for choosing either scheme (aside from the aforementioned collision with our vintage providers) - this RFC aims to address that.

## Moving forward

There are two options moving forward. One is to use the CAPx acronym, and the other is to use the platform name.

### CAPx

Pros:

- Caters for multiple providers per platform (e.g. CAPA and EKS clusters on AWS).
- More uniform than platform names.

Cons:

- Not as descriptive and harder to grok at a glance.

### Platform name

Pros:

- Descriptive and easy to understand.

Cons:

- Creates a 1:1 mapping between provider and plaform (see CAPA vs EKS above).
