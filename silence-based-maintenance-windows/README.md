---
creation_date: 2026-04-28
issues:
- https://github.com/giantswarm/giantswarm/issues/35664
owners:
- https://github.com/orgs/giantswarm/teams/team-atlas
state: review
summary: Use temporary Alertmanager silences and the existing Alerts Timeline dashboard instead of building alert routing to PagerDuty during maintenance operations like cluster upgrades.
---

# Silence-based maintenance windows

## Problem statement

In OpsGenie we had routing rules that directed alerts during cluster upgrades to the engineer responsible for those upgrades. Our current PagerDuty setup does not replicate this capability, creating a risk that upgrade-related alerts are not handled by the right person.

Several approaches to re-implement per-installation alert routing were investigated (see [Alternative solutions](#alternative-solutions)). All of them turned out to be either too expensive, too complex to maintain, or both. After evaluating all options, we concluded that alert routing during maintenance is not strictly necessary if engineers have a way to temporarily silence alerts and a dashboard to monitor the alert situation during the maintenance window.

## Decision maker

@TheoBrigitte (Team Atlas)

## Who is affected / stakeholders

- Team Atlas (owns the observability platform)
- All on-call engineers (affected by alert noise during upgrades)
- Any engineer performing cluster upgrades or other risky maintenance operations

## Preferred solution

Replace per-installation alert routing with **temporary Alertmanager silences** and the **Alerts Timeline dashboard** for situational awareness.

### How it works

When an engineer is about to perform a risky operation (e.g. a cluster upgrade), they:

1. **Create a temporary silence** covering the target installation for the expected duration (e.g. 2-3 hours) using a new CLI tool (`silencectl`).
2. **Monitor the Alerts Timeline dashboard** during the maintenance window to stay aware of any alerts firing on the installation while they are silenced.
3. **The silence expires automatically** after the specified duration, restoring normal alerting behavior.

### Alerts Timeline dashboard

While alerts are silenced and not routed to PagerDuty, they can still be observed on the existing **Alerts Timeline** dashboard. This dashboard is available both on **Grafana Cloud** and on **every installation's local Grafana**. It provides a real-time view of all firing alerts, including silenced ones, allowing the engineer to investigate the ongoing alert situation during maintenance without relying on PagerDuty notifications.

### CLI tool: `silencectl`

A new CLI tool to make creating and managing temporary `Silence` CRs straightforward.

**Core functionality:**
- Create a temporary silence for a given installation with a specified duration
- Support an `--interactive=false` flag for use by automation and AI agents
- Ensure cleanup is respected even when the process is interrupted (not only on explicit `Ctrl+C`)

**Example usage:**
```bash
silencectl create --installation giraffe-prod --duration 2h
```

This tool could also be used in automation scripts, for example during cluster upgrades, potentially replacing the need for inhibition rules.

### Benefits

- **Zero cost** -- works entirely within the current PagerDuty setup and existing Alertmanager infrastructure
- **Simple to maintain** -- no new services to deploy or operate, no sensitive configuration changes at runtime
- **Safe** -- silences are a well-understood Alertmanager primitive; creating one does not touch routing configuration, PagerDuty schedules, or Mimir internals
- **Observable** -- the Alerts Timeline dashboard (available on Grafana Cloud and every installation) gives full visibility into what is firing, even while silenced
- **Automatable** -- the CLI can be integrated into upgrade scripts and automation pipelines

## Alternative solutions

### Mimir Alertmanager config patching CLI

A CLI tool that temporarily patches the Mimir Alertmanager configuration via its API to inject an override route, combined with PagerDuty schedule overrides. This was the initial proposed solution in [giantswarm/giantswarm#35664](https://github.com/giantswarm/giantswarm/issues/35664).

**Why it was rejected:**
- Modifies sensitive Alertmanager configuration at runtime
- The override cannot last more than 12 hours (operator reconciliation window) without additional work
- Cannot support multiple concurrent overrides on different installations through a single PagerDuty service
- Many moving parts (Mimir API, PagerDuty schedules, Teleport auth, port-forwarding) increase the risk of breakage

### Webhook Smart Router (pd-router service)

A Go service deployed between Alertmanager and PagerDuty that reads routing rules from a ConfigMap and uses the PagerDuty Incidents API to assign alerts directly to specific engineers.

**Why it was rejected:**
- Introduces a new service that needs to be deployed and maintained on every installation (to avoid a single point of failure)
- Risk of becoming "its own product" -- a go-to place to hack around PagerDuty limitations, growing in scope over time
- Too much operational burden for a team transitioning to 2 people

## Implementation plan

1. **Build `silencectl`** with support for creating temporary silences per installation, duration-based expiry, graceful cleanup on interruption, and a non-interactive mode.
2. **Document the maintenance workflow** -- write a runbook explaining how to use temporary silences together with the Alerts Timeline dashboard during maintenance operations.
3. **Communicate to on-call engineers** -- announce the new workflow and tooling.

## Future work

- **Scheduled silences** -- extend the `Silence` CR with a start date so that silences can be created ahead of time and activated automatically at a given moment. This would let engineers prepare maintenance windows in advance instead of having to be at the keyboard exactly when the operation starts.

## Communication plan

- Post the RFC PR to `#news-ops` and relevant team channels for review.
- Once approved, announce the new maintenance workflow and `silencectl` tool in `#topic-ops`.
- Update the on-call runbook and maintenance documentation.
