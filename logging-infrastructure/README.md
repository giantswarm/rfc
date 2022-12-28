# Logging infrastructure

As a Giant Swarm engineer, I want to be able to access a history of logs for components managing our platform in order to both investigate ongoing operational issues and provide details for incident reports.

## Context

High level architecture proposal to implement a logging solution.

Atlas started working on a logging infrastructure implementation using [Loki](https://grafana.com/docs/loki/latest/).
So far we worked on a POC towards having a centralized setup.
There were some recent discussions where we learned about other requirements leaning towards a distributed setup, here are the pro and cons details of those setups.

### Distributed setup

* 1 Loki instance for each installation
* Loki is hosted at the installation level

#### Pros

- Satisfy customer requirement towards data isolation (i.e. legal, or data privacy requirements)
- Keep our Platform as a Product model (self-sufficient installation can keep running alone)
- More resilient setup towards failure

#### Cons

- Heterogeneous Object storage (different provider, different requirements, different limitations)

### Centralized setup

* Single central Loki instance
* Loki is hosted by GiantSwarm

#### Pros

- Global view (aka single pane of glass, cross-installation queries)
- Operational cost (1 Loki instance to handle)
- Anomalies detections (multi installation correlated data)

#### Cons

- Cost needs a new billing system and business model

## Conclusion

There is a hard requirement from some customer where no data should leave their installation (due to legal concerns). In order to comply with this we need to adopt a distributed setup.
We currently have some concerns towards the feasibility of implementing Loki on all the different providers we support, due to storage requirements.

## Next steps

- Build a POC with a Loki running inside an installation starting with 1 provider.
  - crossplane and work done on harbour might help us for storage
- Re-evaluate and see how we proceed with other providers and other customer requirements.

## Open questions

- Can we provide a global view on a distributed setup ? (maybe on a data subset)
