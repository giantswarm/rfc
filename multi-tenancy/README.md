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

<img src="./assets/loki-multi-tenancy.png" width="300" alt="Loki multi-tenancy on the read path">

The read path queries `loki` providing an `X-Scope-OrgID` header which contains the identifier of all clusters: the management cluster plus all workload clusters.

### Configuring multi-tenancy on the read path

### Opened questions

## Write path

### Current architecture for the write path

### Configuring multi-tenancy on the write path

#### Metrics

#### Logging

#### Traces/Profiles
