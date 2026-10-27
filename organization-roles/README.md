---
creation_date: 2026-10-27
issues:
- https://github.com/giantswarm/giantswarm/issues/36698
- https://github.com/giantswarm/roadmap/issues/3056
owners:
- https://github.com/orgs/giantswarm/teams/sig-architecture
- https://github.com/orgs/giantswarm/teams/team-bumblebee
- https://github.com/orgs/giantswarm/teams/team-shield
state: review
summary: One set of roles per capability and level, bound per Organization, with a RoleBinding in the Organization namespace as the only source of membership. organization-operator and rbac-operator merge into one operator that every platform reuses to add its own roles per Organization.
---

# Organization roles: one membership source, one operator

## Problem

The Organization is meant to be the tenant on our platform, but each product decides on its own who belongs to it and what they may do:

- **KaaS.** organization-operator creates the `org-<name>` namespace. rbac-operator binds installation-wide customer and Giant Swarm groups. The same customer admin group is admin in every Organization, and also on the whole management cluster.
- **Observability.** `GrafanaOrganization` keeps its own group lists in `spec.rbac`. Tenants come from one list for the whole installation, with no link to an Organization.
- **Agent platform.** `agent-platform:user`, `:editor` and `:admin` are bound in Organization namespaces. muster, workspace-manager and klaus-gateway each add their own membership list on top.

That makes seven places that hold group lists. There are three definitions of an Organization namespace: a label, a name prefix, or both. Groups are spelled three ways: the Dex connector prefix, an optional `oidc:` prefix on the API server, and kagent re-applying its own prefix. A customer can't make someone admin of one Organization without making them admin of all of them. A new product has no pattern to follow, so each one writes its own.

The full inventory, with sources, is on the [Miro board](https://miro.com/app/board/uXjVEVa-IFw=).

## Proposal

### One membership source

"Person X has role R in Organization O" means one thing: a RoleBinding in `org-O` that binds X, or one of X's groups, to R. Every system either asks the API server through `SubjectAccessReview` (kagent already does this) or derives its own configuration from those bindings. No other system stores group lists for membership.

These are not membership and stay as they are: kagent session shares, klaus-gateway thread grants and channel allowlists, and data-source checks that use the person's own GitHub or GitLab access.

### Roles per capability and level

Role names follow the existing `capability:level` convention (`agent-platform:admin`). Every role is a ClusterRole that is bound per Organization namespace.

| Role | Grants | Replaces today | Owner |
|---|---|---|---|
| `agent-platform:user` / `:editor` / `:admin` | Run agents; write agents, workspaces and remote MCP servers; manage models, model keys, egress and connector credentials | The existing roles, muster `mcpserver-editor` and `workflow-editor`, workspace-manager membership | Bumblebee |
| `cluster:user` / `:editor` / `:admin` | See the Organization's clusters and apps; create and upgrade clusters and install apps; cluster-admin on the Organization's workload clusters and policy exceptions. No Secrets below admin. | `read-in-cluster-ns`, `write-in-cluster-ns`, the cluster-admin RoleBinding in the Organization namespace | Shield (Honeybadger for apps) |
| `observability:viewer` / `:editor` / `:admin` | Grafana organization role and tenant read for the Organization; silences and Alertmanager configuration at editor and above | `GrafanaOrganization.spec.rbac` lists, `write-silences` | Atlas |
| `organization:user` | See the Organization, its members, releases and catalogs | `organization-<org>-read`, `read-releases`, `read-default-catalogs` | Shield |
| `organization:admin` | Every capability admin role in the Organization. It may bind only catalogue roles: no `escalate`, no `serviceaccounts/token`, no `pods/exec`. | The customer `write_all` RoleBinding in each Organization namespace | Shield |
| `platform:admin` | Every capability admin in every Organization. Creates Organizations, manages the platform tenant. | Customer `write_all`, `write-organizations`, agent platform team values | Shield |
| `platform:auditor` | Read everything except Secrets and ConfigMaps, plus policy reports | `read-all` | Shield |
| Personas: KaaS Platform User, Non-Tech User, Security Auditor | Aggregated from the capability roles above, for example Non-Tech User = `agent-platform:user` + `observability:viewer` | Ad hoc bindings | Shield, each platform labels its roles |

Finer roles come later by splitting a role and aggregating the parts back under the same name. Bindings that already exist keep working.

### Merge organization-operator and rbac-operator

Both operators are owned by Shield and work on the same objects: Organizations, their namespaces and the RBAC inside them. rbac-operator still runs on operatorkit (roadmap#3056); organization-operator is kubebuilder on controller-runtime. We merge rbac-operator's controllers into organization-operator.

- **CRDs.** `Organization` (`security.giantswarm.io`) and `RoleBindingTemplate` (`auth.giantswarm.io`) keep their API groups and versions, so no consumer changes.
- **Carried over.** RoleBindingTemplate, the Flux and automation ServiceAccount bindings (with their scope reviewed, see Migration), release and catalog read access, the Crossplane edit binding, and app-operator RBAC in cluster namespaces.

### The contract a platform follows

The merged operator is what every platform reuses for its own roles. It relies on Kubernetes [aggregated ClusterRoles](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#aggregated-clusterroles) rather than a new API.

1. A platform ships its ClusterRoles in its own chart, named `<capability>:<level>`. Each is labelled `organization.giantswarm.io/role: "true"`, plus the `organization.giantswarm.io/aggregate-to-*` labels of the roles it joins (`user`, `admin`, `auditor`, `platform-admin`, and personas).
2. The operator owns the aggregated roles: `organization:user`, `organization:admin`, `platform:auditor`, `platform:admin` and the personas. A labelled role joins them without any change to the operator.
3. The operator keeps the `bind` `resourceNames` of `organization:admin` in sync with the labelled roles. An Organization admin can bind only catalogue roles, and Kubernetes escalation checks do the rest.
4. For each Organization, the operator creates the namespace with the `giantswarm.io/organization` label (the only definition of an Organization namespace), `organization-<org>-read`, and the default bindings from RoleBindingTemplates.
5. Runtime checks use `SubjectAccessReview`. Components that need a list of groups, such as workload-cluster admin groups or Grafana `org_mapping`, use one Go package published by the operator, `pkg/membership`, which answers "subjects holding role R in Organization O" and resolves aggregation once. Organization status holds no copy of the membership.

The test for this design: Atlas adds `observability:*` and Bumblebee adds `agent-platform:*` with changes to their own charts only.

## Capability check

The proposal keeps every capability we have today, except for the rows marked **decide**. Those need an answer before this RFC is approved.

| Today | In this proposal |
|---|---|
| RoleBindingTemplate | Kept in the merged operator |
| Customer `write_all` is cluster-admin on the whole management cluster | **Decide:** becomes `platform:admin`, which covers every Organization and creates Organizations. First list what customers do outside Organization namespaces today. |
| Automation ServiceAccount per Organization, with cluster-wide extras | **Decide:** bound to `organization:admin` without the cluster-wide extras. Customer CI that uses its token needs a deprecation window. |
| Flux runs as cluster-admin in Organization namespaces | A per-Organization Flux ServiceAccount at editor level. Giant Swarm-owned Flux objects get their own. |
| App configuration Secrets, written through `write-in-cluster-ns` | **Decide:** `cluster:editor` has no Secrets. Options are External Secrets or SOPS only, or create without read. |
| kubectl-gs client certificates (they need the cluster CA Secret) | `cluster:admin` only |
| Workload-cluster admin groups | Derived only from `cluster:admin` bindings |
| Customer `rbacBootstrap` overrides on workload clusters | Kept |
| Grafana Admin, Editor, Viewer per GrafanaOrganization | Projected from `observability:*` bindings |
| Silences and Alertmanager configuration | `observability:editor` and above |
| `agent-platform:platform-user` for every signed-in person in the `kagent` namespace | Kept |
| workspace-manager members by group, email or **domain** | **Decide:** RBAC has no domain subject. Either an IdP group per domain, or drop domain membership. |
| Crossplane edit for customer admins | `platform:admin`, or a Crossplane capability role with a named owner |
| `read-all` | `platform:auditor`, plus the Giant Swarm Security Grafana organization |
| Teleport and Giant Swarm staff groups | Unchanged |

## Prerequisites

Before any new role ships:

1. Workload-cluster admin groups are derived only from `cluster:admin` bindings. Until then, workload-cluster roles cannot follow Organization bindings.
2. In Organization namespaces, Flux runs only as the Organization's Flux ServiceAccount. A Flux object can't pick another ServiceAccount or a kubeconfig (Flux `--default-service-account`, `--no-cross-namespace-refs`, and a stricter `flux-multi-tenancy` policy). Without this, editor is the same as admin.
3. One definition of an Organization namespace: the label. muster drops its `org-` prefix rule.
4. One group spelling across Dex, the API server and kagent.

## Migration

1. Ship the merged operator with the current behaviour (no role changes) and retire rbac-operator.
2. Ship the catalogue and aggregated roles next to today's roles. Existing role names aggregate into the new ones, so current bindings keep working.
3. Replace the customer `write_all` groups with one bootstrap binding of `platform:admin` per installation, through RoleBindingTemplate.
4. Rewrite customer bindings that use the `oidc:` group prefix to the single spelling, with a report of the bindings changed per installation.
5. Move each consumer to SubjectAccessReview or `pkg/membership`: dex-operator, observability-operator, muster, workspace-manager. Remove their group-list values.
6. Remove old role names after one release cycle with no bindings left.

## Open questions

- Do we need a team below the Organization, or is the Organization the team and the cost centre?
- Do workload-cluster roles follow Organization bindings, or stay per cluster?
- Who should see the Shared Org and the `giantswarm` tenant?
- MCP server and workspace app grants differ, and there's no per-agent limit yet. Does that need a role?

## Decisions

### 2026-10-27 Customers build their own roles inside their Organization

Customers create Roles in their own Organization namespace, limited to rights they already hold. A security review happens before this ships.

### 2026-10-27 Both write-organizations and an Organization manager are supported

Installation-wide Organization creation stays available, next to a role that manages one Organization.

### 2026-10-27 Roles are per capability now, finer roles come later by splitting

A split role is aggregated back under its old name, so existing bindings keep working.

### 2026-10-27 Role names keep the capability:level form without a gs: prefix

This matches the existing `agent-platform:*` roles.

### 2026-10-27 Harnesses stay in the kagent namespace for everyone

There are no copies of a harness per tenant.
