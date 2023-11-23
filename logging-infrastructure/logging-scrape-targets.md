---
creation_date: 2023-11-23
issues:
- https://github.com/giantswarm/roadmap/issues/2756
owners:
- https://github.com/orgs/giantswarm/teams/team-atlas
state: review
summary: Definition of logging scrape targets
---

# Logging scrape targets

### Introduction

Team Atlas has proposed a solution in order to collect, store and access Logs
using [Loki](loki-url), [Promtail](promtail-url), and [Grafana](grafana-url).

Where :
- Loki acts as the main component in charge of storing and retrieving Logs from storage.
- Promtail is our in-cluster agent in charge of collecting Logs and sending them over to Loki.
- Grafana is there to provide our user's read access to those Logs.

In order to retrieve Logs data one have to define which targets to collect Logs from
in Promtail's configuration.

This RFC defines for which targets Logs are collected from.

### Logging interface definition

Management and Workload cluster are currently handle differently as GiantSwarm
operate all components in Management cluster while only part of components
running on Workload clusters are operated by GiantSwarm.

#### Management cluster

On Management cluster following Logs are collected:

- Kubernetes Pods: Logs are collected for all Pods' containers discovered in Kubernetes API
- Kubernetes Audit logs: Logs are collected from Kubernetes API Server audit logs via `/var/log/apiserver/*.log` files
                         This includes all namespaces activity.
- systemd Logs: Logs are collected from both `/var/log/journal` and `/run/log/journal` directories.

#### Workload cluster

On Workload cluster following Logs are collected:

- Kubernetes Pods: Logs are collected for Pods' containers discovered in Kubernetes API within the `kube-system` and `giantswarm` namespaces.
- Kubernetes Audit logs: Logs are collected from Kubernetes API Server audit logs via `/var/log/apiserver/*.log` files
                         This includes all namespaces activity.
- systemd Logs: Logs are collected from both `/var/log/journal` and `/run/log/journal` directories.

#### Limitation

The configuration for Logs scrape targets is currently set and defined in our
[logging-operator](logging-operator-url). This means it can currently only be
changed by releasing a new version of the logging-operator.

[loki-url](https://github.com/grafana/loki#readme)
[promtail-url](https://grafana.com/docs/loki/latest/send-data/promtail/)
[grafana-url](https://github.com/grafana/grafana#readme)
[logging-operator-url](https://github.com/giantswarm/logging-operator/)
