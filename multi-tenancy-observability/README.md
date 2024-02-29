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

Moving towards our observability platform, we have to consider to important topics.

First, we generate a lot of observability data.
For instance, we reached our ingestion limits in Prometheus more than a year ago and each new component we add brings a lot more metrics so we have to be mindful about the metrics we keep.
This issue got a whole lot bigger when we added logging with Loki to the mix.

Second, our product presentlyallows anyone with access to Grafana on the management clusters to access all the data (metrics and logs) for all workload clusters without any kind of data seggregration. This is part of the reason why only a subset of our customers (generaly only the platform teams) have access to our managed grafana and is also why our shared installation grafana is not accessible to customers.


As part of the developer platform, we want to be able to ingest all sorts of customer observability data. This will require Giant Swarm observability platform to be able to provide data isolation between tenants.

To that end, we now need to move towards multi-tenancy in our observability.

## Current situation

### Our Logging stack

Our logging solution Loki supports multi-tenancy based on a http header (`X-Org-ID`) and we already had to implement some basic form of multi-tenancy to be able to support the logs coming from our clusters.

The graph below shows our current implementation of the multi-tenancy on logs:

<img src="./assets/scope-orgid.png" width="500" alt="Loki multi-tenancy and X-Scope-OrgID header">

### Future of monitoring

We already have plans to migrate our monitoring stack to Grafana Mimir, which supports the same multi-tenancy mechanism as Loki. You can see the current status in this [epic](https://github.com/giantswarm/roadmap/issues/3039).

## What we want to achieve

We want to be able to segregate access to the observability data based on the user groups they have configured in their active directory.

But we also want to provide flexibility to customers to allow them to isolate their data as they want.
For instance, some customers may want to map:
- 1 tenant to 1 namespace
- 1 tenant to 1 cluster
- multiple tenants to 1 application (e.g. ingress controllers)
We would like to propose our customers the option of defining their tenants so that they can isolate the data as they want.

__Disclaimer:__ We might change this flexibility later on based on product (e.g. project CR) or operational decisions ( e.g. too many tenants).

In this document we will talk mostly about the logging implementation (with `Loki`) as this is where we are the more advanced, but we expect to share the same logic for all our observability stack components.

Because the read and write path for the multi-tenancy is technically different and have different requirements, we decided to split it into different sections.

## Read path

### Current architecture for the read path

Below is a graph exposing the current state of multi-tenancy:

<img src="./assets/current-multi-tenancy.png" width="300" alt="Loki multi-tenancy on the read path">

The read path queries `loki` providing an `X-Scope-OrgID` header which contains the identifier (the `read` tenant) of all clusters: the management cluster plus all workload clusters.

### Configuring multi-tenancy on the read path

We have asserted that we can retrieve users groups through the OAuth token that is received from Grafana when we enable Oauth forwarding on the Loki datasource.

Below is an example of OAuth token content coming from Dex:

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

The component `loki-multi-tenant-proxy` which has now been renamed to `grafana-multi-tenant-proxy` should be configured with the mapping between groups of people and tenants

Below is a proposal of such a configuration:

```yaml
groups:
- name: giantswarm-admins
  tenants:
  - mc-name
  - wcdev-name
  - wcprod-name
- name: Developers
  tenants:
  - wcdev-name
- name: Ops
  tenants:
  - wcdev-name
  - wcprod-name
...
```

The mapping configuration should be dynamically created and updated regardless of the data source by an operator.
The operator would be able to reconcile any kind of data source and generate the configuration expected by `grafana-multi-tenant-proxy`.

Below is a graph exposing multi-tenancy proposal:

<img src="./assets/future-multi-tenancy.png" width="300" alt="Multi-tenancy proposal on the read path">

#### Operator management

`logging-operator` is an existing component responsible for creating a secret for the multi-tenant-proxy. That secret contains a mapping between credentials and tenant (it's currently equivalent to the cluster id).

We will have to either create a new operator to handle multi-tenancy for all observability tools (`observability-multi-tenancy-operator`) or add this feature into the `logging-operator` and rename it to `observability-operator`.

We are open to suggestions on this topic.

### Opened questions

#### Teleport issue

We are currently facing an issue with `teleport` authentication:
[Teleport JWT issue](https://github.com/giantswarm/giantswarm/issues/29719)

We are authenticated on Grafana through a JWT token provided by teleport.
But that token is not forwarded to the datasource as this is not using the Grafana OAuth plugin to authenticate. Due to this, we cannot access the users groups in the grafana-multi-tenant-proxy.

We are considering a number of options that are not ideal at the moment:

- having double datasource: one for customer with OAuth authentication and another dedicated to GiantSwarm people authenticated throw teleport.
- having double grafana (same idea than above but for the all grafana instance, not just the datasource).
- share an authentication secret via cookies.
- other ideas are welcome!

#### Mapping user's groups to tenants

What interface could we offer our customers to enable them to define the mapping between their groups and their tenants:

- Custom resources like TenantCR, GroupCR
- UI in happa
- other ideas ?

## Write path

### Current architecture for the write path

### Configuring multi-tenancy on the write path
