---
creation_date: 2024-09-26
issues:
- https://github.com/giantswarm/giantswarm/issues/31646
last_review_date: 2025-03-10
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: Decide whether the apps in CAPI cluster should have or not a prefix, and if we need to enforce it.
---

# App prefix

## Intro

When we moved to Cluster API, we decided that all resources would live the organization namespace. That decision means apps, including the cluster app, from different clusters coexist in the same namespace. It also means, it forces us to name the apps differently to avoid conflicts. [More information in the following discussion](https://github.com/giantswarm/workload-clusters-fleet/pull/802#issuecomment-1946218047)

## Scope

This affects `kubectl gs` since we have a mix of functionality. In `gitops` subcommand we append the cluster id as a prefix on the output but in `template` subcommand the user needs too add explicitly the `--app-name` with the prefix on it.

When users use the GitOps template, we advocate relying on the `namePrefix` variable to prefix the apps and config maps automatically.

Lately, happa has also prefixed the apps automatically.

We don't validate or mutate the app name via the management cluster API.

## Solution

We decided to not enforce the cluster prefix but encourage customers to use it as good practice.

### API enforcement

- The app admission controller will validate the name of the apps when deploying to the organization namespace to avoid collisions and conflicts that can unexpectedly affect customers.

- The app admission controller will warn the user when creating an application with no prefix or a prefix that does not match any existing cluster.

We unify the behavior across all the tools and commands. The kubectl's `gitops` commands will no longer auto prefix the apps in a newer version.

## Alternatives

### Do not enforce

Leave the customer the freedom to name the apps as they want. This will impact neglected customers who forgot to prefix their apps, potentially unintentionally uninstalling apps or moving to clusters. We will let them choose what type of convention they take.

We could potentially hide it from the customer. This would make the user experience more friendly, but it would also make debugging harder. Our `kubectl-gs` command could get the app without the need for a prefix, or the portal could show the app without containing the prefix.

## References

- [Discussion](https://github.com/giantswarm/workload-clusters-fleet/pull/802)
