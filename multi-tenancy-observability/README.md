---
creation_date: 2024-02-08
issues:
- https://github.com/giantswarm/roadmap/issues/2771
owners:
- https://github.com/orgs/giantswarm/teams/team-atlas
state: review
summary: How Giant Swarm manages multi-tenancy to isolate observability data per tenants (i.e. metrics, logs, traces).
---

# Multi-tenancy for observability

## Glossary

- `tenant`: a group of users who share a common access with specific privileges to observability data
- `observability data`: all data related to metrics, logs, traces, profiles
- `read path`: path used by users to access observability data
- `write path`: path used by components to store observability data

## Introduction

Giant Swarm managed components produce a lot of observability data (metrics, logs, traces and so on).
For instance, we have reached our ingestion limits in Prometheus more than a year ago.
On top of this, as part of the developer platform, we want to be able to ingest all sorts of customer observability data and provide data isolation between tenants.

To that end, we now need to move towards multi-tenancy in our observability stack.
Thankfully, our logging solution Loki supports multi-tenancy based on a http header (`X-Org-ID`) and we already had to implement things.
The graph below shows our current implementation of the multi-tenancy on logs:

<img src="./assets/scope-orgid.png" width="500" alt="Loki multi-tenancy and X-Scope-OrgID header">

To be able to support multi-tenancy in our monitoring stack, we are currently working on moving to mimir on CAPI as mimir supports the same multi-tenancy mechanism as Loki, see our current status on the [epic](https://github.com/giantswarm/roadmap/issues/3039).

According to the role of people, some data must be accessible or not.
We would like to propose our customers the option of defining their tenants so that they can isolate the data as they want.

Presently, our product allows anyone with access to Grafana to request all the data (metrics and logs) for all tenants. This is part of the reason why only a subset of our customers (only the platform teams) have access to our managed grafana and is also why our shared installation grafana is not accessible to customers.

Our idea of multi-tenancy is to be able to isolate data per tenant. A tenant can be anything: a namespace, a cluster id, a group of people, a feature, etc.

In this document we will talk mostly about the logs (with `Loki`), but we expect to share the same logic for all our observability stack components.

Because the read and write path for the multi-tenancy is technically different, we decided to split it into different sections.

## Read path

### Current architecture for the read path

Below is a graph exposing the current state of multi-tenancy:

<img src="./assets/current-multi-tenancy.png" width="300" alt="Loki multi-tenancy on the read path">

The read path queries `loki` providing an `X-Scope-OrgID` header which contains the identifier of all clusters: the management cluster plus all workload clusters.

### Configuring multi-tenancy on the read path

Our idea to handle multi-tenancy on the read path is to map group of people with tenants.
We can retrieve those groups of people through the OAuth token received from Grafana.
Below an example of OAuth token content coming from Dex:

```json
{
  "iss": "https://dex.golem.gaws.gigantic.io",
  "sub": "XXXXXXX",
  "aud": "YYYYYYY",
  "exp": 1705661375,
  "iat": 1705659575,
  "email": "people@giantswarm.io",
  "email_verified": true,
  "groups": [
    "giantswarm-ad:giantswarm-admins",
    "giantswarm-ad:GS Support - MS teams",
    "giantswarm-ad:Giant Swarm Global",
    "giantswarm-ad:GiantSwarm",
    "giantswarm-ad:Giant Swarm EU",
    "giantswarm-ad:Developers"
  ],
  "name": "People People"
}
```

The component `loki-multi-tenant-proxy` should be renamed `grafana-multi-tenant-proxy` to be more generic because it will handle multi-tenancy for logs, metrics, traces, etc.
That component should have a configuration in which the mapping between groups of people and tenants is defined.

Below a proposal of such a configuration:

```yaml
groups:
- name: giantswarm-admins
  tenant_ids:
  - mc-name
  - wcdev-name
  - wcprod-name
- name: Developers
  tenant_ids:
  - wcdev-name
- name: Ops
  tenant_ids:
  - wcdev-name
  - wcprod-name
...
```

That configuration should be dynamically created and updated regardless of the data source.
We are thinking of having an operator to manage that mapping. The operator would be able to reconcile any kind of data source and generate the configuration expected by `grafana-multi-tenant-proxy`.

Below is a graph exposing multi-tenancy proposal:

<img src="./assets/future-multi-tenancy.png" width="300" alt="Multi-tenancy proposal on the read path">

### Opened questions

#### Teleport issue

We are currently facing an issue with `teleport` authentication:
[Teleport JWT issue](https://github.com/giantswarm/giantswarm/issues/29719)

We are authenticated on Grafana through a JWT token provided by teleport.
But that token is not forwarded to the datasource.
So we are not able to authenticate the user into the multi-tenant proxy.
We are considering a number of options that are not ideal at the moment:

- having double datasource: one for customer with OAuth authentication and another dedicated to GiantSwarm people authenticated throw teleport.
- having double grafana (same idea than above but for the all grafana instance, not just the datasource).
- share an authentication secret via cookies.
- other ideas are welcome!

#### Operator

`logging-operator` is an existing component responsible for creating a secret for the multi-tenant-proxy. That secret contains a mapping between credentials and tenant (it's currently equivalent to the cluster id).

- Do we add a feature in that operator to handle the multi-tenant-proxy configuration we described above ?
- In that case, we should rename it: any suggestion ?
- If we don't reuse `logging-operator`, we will need to implement a new one: any suggestion for its name ?

#### Mapping groups-tenants

What interface could we offer our customers to enable them to define the mapping between their groups and their tenants:

- Custom resources like TenantCR, GroupCR
- UI in happa
- other ideas ?

## Write path

### Current architecture for the write path

### Configuring multi-tenancy on the write path

#### Metrics

#### Logging

#### Traces/Profiles
