# RFC 0003 - Monitoring System End To End Tests

We're currently building a monitoring system that supports a large number of
Kubernetes clusters by provisioning Prometheus servers for each monitored
cluster in a sharded architecture. We would like to have end-to-end tests for
this system that ensure it functions correctly and to prevent regressions.

## Summary of the Monitoring System

The system is built initially with Giant Swarm architecture in mind where each
installation has a _Management Cluster_ where monitoring and infrastructure
operators live and a number of _Workload Clusters_ where customers' workloads
live.

The system consists of [prometheus-meta-operator][] which reacts to clusters
being created/deleted either via [Cluster-API][] or GS-specific API by
provisioning/maintaining/deprovisioning Prometheus instances (via
[prometheus-operator][]), [OpsGenie][] heartbeats and other associated
resources. Another component is [Promxy][] which brings all the per-cluster
shards together and makes them appear as a single API endpoint to the user.

## Testing Goals

We would like the tests to cover the following:

1. Deployment:

  - ensure all components are installable together; this is to catch any issues
    with Helm charts, etc.

  - ensure that components are installable on all supported infrastructure
    providers; this is again to catch any issues with Helm charts or templating

2. Provisioning/Deprovisioning operation:

  - ensure that all required resources are created/cleaned-up in reaction to
    cluster provisioning/deprovisioning respectively; this is to catch bugs and
    regressions in _prometheus-meta-operator_

  - ensure the required Prometheus instances are provisioned and running
    correctly; this is to catch issues with configuration for Prometheus that
    we generate

3. Monitoring system operation:

  - ensure that all built-in/configured targets are configured in provisioned
    Prometheus instances; this is to catch issues with configuration we
    generate and catch regressions when monitored components change

  - ensure that provisioned Prometheus instances ingest the metrics we need for
    alerting; this is to catch issues with configuration and regressions when
    monitored components change

## Test Infrastructure

Given the above goals, we'd ideally need a system that is able to provision
clean _Management Cluster_ environments into which we could deploy the system
and which is then able to provision specifically configured
_Workload Clusters_ to test the monitoring system operation.

## Open Questions

1. Testing everything against all supported providers may not be necessary,
   could we split the tests into provider-independent tests which could even be
   run on a light-weight infra (like KinD or similar) and provider-dependent
   ones that need real infra?

2. I think we can leave the question of triggering the tests for later once we
   have something more concrete, for now even being able to trigger such tests
   manually before a release would be OK. Right?

3. Do we have / have plans for anything that would satisfy the test
   infrastructure needs?

[Cluster-API]: https://github.com/kubernetes-sigs/cluster-api/
[OpsGenie]: https://docs.opsgenie.com/docs/api-overview
[prometheus-operator]: https://github.com/prometheus-operator/prometheus-operator/
[prometheus-meta-operator]: https://github.com/giantswarm/prometheus-meta-operator/
[Promxy]: https://github.com/jacksontj/promxy/
