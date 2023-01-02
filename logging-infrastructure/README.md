# Logging infrastructure

As a Giant Swarm engineer, I want to be able to access a history of logs for components managing our platform in order to both investigate ongoing operational issues and provide details for incident reports.

## Context

Atlas started working on a logging infrastructure implementation using [Loki](https://grafana.com/docs/loki/latest/).
So far we worked on a POC towards having a centralized setup, where a central Loki instance hosted by GiantSwarm ingests logs from our installations.
There were some recent discussions where we learned about other requirements leaning towards a distributed setup, here are the pro and cons details of those discussions.

### Distributed setup

What we call distributed setup, is when there is 1 Loki instance hosted on each installation.
So logs are stored and accessible on a per installation basis.

#### Pros

- Satisfy customer requirement towards data isolation (i.e. legal, or data privacy requirements)
- More resilient setup towards failure
- Keep our Platform as a Product model (self-sufficient installation can keep running alone)

#### Cons

- Heterogeneous Object storage (different provider, different requirements, different limitations)

### Centralized setup

What we call centralized setup, is when there is a single central Loki instance hosted by GiantSwarm.
So logs are stored and accessible in a single and central place.

#### Pros

- Global view (aka single pane of glass, cross-installation queries)
- Operational cost (1 Loki instance to handle)
- Anomalies detections (multi installation correlated data)

#### Cons

- Cost needs a new billing system and business model
- Customer does not own their data (i.e. lose logs access when leaving GiantSwarm)
- Requires good connectivty from installations to Loki (i.e. edge cluster might be a problem)

## Conclusion

There is a hard requirement from some customer where no data should leave their installation (due to legal concerns).
In order to comply with this requirement we need to adopt a distributed setup.
We currently have some concerns towards the feasibility of implementing Loki on all the different providers we support, due to storage requirements.

## Next steps

- Build a POC with a Loki running inside an installation starting with 1 provider.
- Re-evaluate and see how we proceed with other providers and other customer requirements.

## Open questions

- Can we provide a global view on a distributed setup ?