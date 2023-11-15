---
creation_date: 2021-11-10
state: approved
---

# Configuration management with Cluster API

This RFC describes how we can handle configuration management with Cluster API - focusing on defaulting, upgrades and interactions.

## Context

During our transition to `cluster-api` we have decided to no longer directly couple operator versions to cluster versions.
The version of a cluster should completely be determined by the configuration of the cluster.
An example to show this changed approach is the following:
- Cluster `deu01` has configuration `X` and is reconciled by `capi-controller` in version `1.1.0`.
- `capi-controller` is updated to version `1.2.0`. Cluster `deu01` remains completely unchanged.
- A new cluster `peu01` with configuration `X` is exactly the same as `deu01`.
- The configuration of `deu01` is changed to `Y` which causes the cluster to upgrade.
The lifecycle of the cluster is therefore fully determined by its configuration and no longer determined by the operator reconciling it.

_A new concept for Giant Swarm: releases are completely decoupled from the operators and only consist of cluster configuration!_

## Content

This RFC contains three parts which are in decreasing level of maturity:
- [Releases as gitops managed configmaps](0_capi-releases.md)
- [Sharing responsibility and customization with customers](1_default-customization.md)
- [Re-using release structures for gitops cluster management](2_gitops-management.md)

We plan to use this RFC to have an open discussion on these topics before writing a more technical spec.
Please voice concerns as well as alternative ideas here.
