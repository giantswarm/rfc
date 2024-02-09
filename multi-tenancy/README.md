---
creation_date: 2024-02-08
issues:
- https://github.com/giantswarm/roadmap/issues/2771
owners:
- https://github.com/orgs/giantswarm/teams/team-atlas
state: review
summary: How GiantSwarm manages multi-tenancy to isolate data by tenants (i.e. metrics, logs, traces).
---

# Multi-tenancy proposal

## Introduction

Since we have a logging infrastructure, we are thinking about the multi-tenancy.
The observability stack with metrics, logs, traces is treating a lot of data.
According the role of people, some data must be accessible or not.
We would like to propose our customers the option of defining their tenants so that they can isolate the data as they want.

Our product currently allows anyone with access to Grafana to request all the data: metrics and logs.
Those datas are written with a tenant id that corresponds to the cluster id.

Our idea of multi-tenancy is to be able to isolate data by tenant. A tenant can be anything: a namespace, a cluster id, a group of people, a feature, etc.

We need to discuss how we handle multi-tenancy when accessing data (read path) and when sending it to object storage (write path).

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

Below a proposal such of configuration:

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
We are thinking of having an operator to manage that mapping. The operator will be able to reconcile any kind of data source and generate the configuration expected by `grafana-multi-tenant-proxy`.

Below is a graph exposing multi-tenancy proposal:

<img src="./assets/future-multi-tenancy.png" width="300" alt="Multi-tenancy proposal on the read path">

### Opened questions

#### Teleport issue

We are currently facing an issue with `teleport` authentication:
[Teleport JWT issue](https://github.com/giantswarm/giantswarm/issues/29719)

We are authentified on Grafana through a JWT token provided by teleport.
But that token is not forwarded to the datasource.
So we are not able to authenticate the user into the multi-tenant proxy.
We are considering a number of options that are not ideal at the moment:

- having double datasource: one for customer with OAuth authentication and another dedicated to GiantSwarm people authenticated throw teleport.
- having double grafana (same idea than above but for the all grafana instance, not just the datasource).
- other ideas are welcome!

## Write path

### Current architecture for the write path

### Configuring multi-tenancy on the write path

#### Metrics

#### Logging

#### Traces/Profiles
