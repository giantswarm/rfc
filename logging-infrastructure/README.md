# Logging infrastructure

As a Giant Swarm engineer, I want to be able to access a history of logs for components managing our platform in order to be to both investigate ongoing operational issues and provide details for incident reports.

## Proposals

High level architecture proposal to implement a logging solution.

### Distributed (per installation) setup

Having 1 Loki instance per installation

### Pros
- Satisfy customer requirement towards data privacy (data stays in customer hands)
- Cost re-use our current billing system
- Keep our Platform as a Product model (self-sufficient installation can keep running alone)
- Resilient setup
### Cons
- Operational cost (many Lokis instance to handle)
- Heterogeneous Object storage (different provider, different requirements, different limitations)
- No global view (aka single pane of glass, no cross-installation queries)

## Centralized setup

Having a single Loki instance hosted by GiantSwarm

### Pros
- Global view (aka single pane of glass, cross-installation queries)
- Anomalies detections (multi installation correlated data)
- Operational cost (1 Loki instance to handle)

### Cons
- Data privacy (data stored in GiantSwarm account)
- Cost needs a new billing system and business model
- Single point of failure

## Decision

<tbd>

## Requirements

- object storage provisioning

### Next steps
- how to automate object storage provisioning ?
- can we provide a global view on a distributed setup ? (maybe on a data subset)
