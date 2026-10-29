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
summary: Per-Organization roles for the agent platform. Three roles, agent-platform:user, editor and admin, bound in the Organization namespace, with a naming and labelling scheme other capabilities can reuse. Membership is the RoleBinding, nothing else. Checks outside the Kubernetes API use a SubjectAccessReview with a fixed verb and resource. Two open questions for Shield before the rest is written.
---

# Organization roles for the agent platform

## TL;DR

- The agent platform needs per-Organization roles. Today nobody can be made admin of the agent platform in one Organization without also getting workload-cluster kubeconfigs and the Organization's `automation` ServiceAccount.
- We want three roles, `agent-platform:user`, `agent-platform:editor` and `agent-platform:admin`, bound per Organization namespace, and a way of doing it that other teams can reuse for their own capabilities later.
- A person has a role in an Organization when a RoleBinding in that Organization's namespace says so. No other list of people.
- Roles are ClusterRoles named `<capability>:<level>` and labelled so an operator knows which ones it may bind. Decisions outside the Kubernetes API are a `SubjectAccessReview` with a fixed verb and resource, which is what kagent-extensions does today.
- Two questions need Shield's answer before the rest is written: one operator for the bindings, and how admin-written Secrets can live in an Organization namespace next to the workload-cluster kubeconfigs. If the shared namespace cannot be made safe, the fallback is a Bumblebee operator with an `org-<name>-agents` namespace per Organization.

## The problem

The agent platform is multi-tenant by Organization. An Organization's agents, MCP servers, workspaces, toolchains and models live in its `org-<name>` namespace on the management cluster, next to its clusters. A customer wants to say "Alice can run our agents", "Bob can also write them" and "Carol can also manage the MCP servers and their credentials", for one Organization, without Giant Swarm in the loop.

Today that is not possible:

- The documented way to make someone admin of an Organization is to bind `cluster-admin` in its namespace. dex-operator and cluster-manager read that binding as "admin of the Organization's workload clusters", and `cluster-admin` in the namespace lets the subject mint a token for the Organization's `automation` ServiceAccount, which holds rights outside the namespace (`crossplane-edit`, `write-silences`, `patch-charts` in `giantswarm`, policy exceptions). So "admin of the agent platform in Payments" gives much more than the agent platform.
- The three `agent-platform:*` ClusterRoles exist (shipped by agent-platform-connectivity) but nothing of ours binds them in an Organization namespace. On gazelle the only bindings are the platform tenant's, in the `kagent` namespace, from chart values. On graveler two test Organizations carry an `agent-platform:editor` binding, applied by a Flux kustomization (`tenant-tests`) in our GitOps repo.
- The agent platform's own managers do not use them. Each keeps its own list of people:

| Place | What it holds |
|---|---|
| Installation values `oidc.customer.write_all_groups` | Customer admin groups, `cluster-admin` everywhere (rbac-operator) |
| RoleBindings in `org-<name>` | Read by rbac-operator, dex-operator and cluster-manager, each with its own idea of what they mean |
| agent-platform values `tenants.platform.users`, `.editors`, `tenants.platformTeam` | Who sees and edits the platform tenant's agents |
| muster values `rbac.mcpServerEditor.subjects`, `rbac.workflowEditor.subjects`, and the `agent-platform:mcpserver-viewer` binding | Who lists and writes MCPServers and Workflows, in muster's namespace |
| workspace-manager values | Groups, emails and domains that may use Workspaces |
| toolchain-manager values | Owners who approve toolchain sources |
| klaus-gateway `channelAllowlist` | Which Slack channels may talk to an agent |
| kagent-extensions machine-caller and session-reader allowlists | ServiceAccounts that may call the API or read sessions |
| Workload-cluster `rbacBootstrap` values | Admin groups on each workload cluster |

A new capability has no pattern to follow, each one invents its own, and the customer has to learn all of them.

### What this RFC protects

The Organization's agent-platform objects on the management cluster: Agents, Sessions, RemoteMCPServers and muster MCPServers, the Secrets they reference, Workspaces, toolchain sources, ModelConfigs and EgressPolicies. The check is on the management-cluster API, plus the two managers that decide outside it today (workspace-manager, toolchain-manager), which must ask the API server instead of keeping their own list.

Not covered: workload-cluster RBAC, the KaaS roles, observability, and agent identity (an agent as a subject of its own). See [What this RFC does not do](#what-this-rfc-does-not-do).

## The three roles

Each level includes the ones below it. The rules as shipped today are in the [appendix](#appendix-agent-platform-role-rules-as-shipped).

| Role | May | May not |
|---|---|---|
| `agent-platform:user` | See the Organization's agents, MCP servers, workspaces and toolchains; start sessions; use workspaces and toolchains | Write anything |
| `agent-platform:editor` | Also create and edit agents, workspaces and toolchain sources, and the HelmRelease and OCIRepository agent-manager writes on the caller's behalf | Touch credentials or members |
| `agent-platform:admin` | Also manage MCPServers and the Secrets they use (create, replace, delete, never read back), ModelConfigs and EgressPolicies; bind people in the Organization to the three roles | Anything beyond the agent platform |

No role gets a workload-cluster kubeconfig, a token for the `automation` ServiceAccount, `get`, `list` or `watch` on Secrets, `escalate`, `impersonate`, or anything in another Organization.

"Admin of Payments" in this RFC means exactly the third row, in `org-payments`, and nothing else.

Harnesses are defined once, in the `kagent` namespace, and agent-manager copies them into each tenant namespace (graveler: `org-agent-platform-test-b/kagent`, managed by agent-manager). An Organization admin does not write harnesses; whether they ever will is not part of this RFC.

## How it works

**Roles.** A role is a ClusterRole named `<capability>:<level>` with two labels, one for the capability and one for the level (label keys to be agreed, see [Open questions](#open-questions)). Each team ships its own roles in its own chart. A capability spread across several charts builds its roles with native aggregated ClusterRoles. The labels tell the operator which ClusterRoles it may bind and which names an admin may `bind` to.

**Levels.** The level names mean the same kind of access everywhere, not the same resources, because the resources belong to each capability: `user` reads, `editor` writes the capability's own objects, `admin` also manages credentials and members for that capability. A team may ship fewer than three levels.

**Membership.** A person has a role in an Organization when a RoleBinding in the Organization namespace binds them, or one of their groups, to that role. That binding is written in one of two ways, both existing:

- an `agent-platform:admin` creates it directly. The API server enforces that an admin may `bind` only the three `agent-platform:*` names (`bind` with `resourceNames`, already in the shipped role);
- Giant Swarm or a customer platform admin stamps it into every matching Organization with a `RoleBindingTemplate` (rbac-operator, `spec.scopes.organizationSelector`), as is done today for Flux and the `automation` ServiceAccount.

The operator's job for this RFC is small: keep the admin role's `bind` list in sync with the labelled ClusterRoles, and stamp RoleBindingTemplates, which it does already. Which operator that is (rbac-operator, organization-operator, or one of ours) is a separate decision.

**Checks outside the API server.** A program that decides access for something that is not a Kubernetes object asks the API server with a `SubjectAccessReview` for one fixed verb and resource per decision, so two programs asking the same question get the same answer. kagent-extensions does this today with its Kubernetes authorizer and reuses an answer for the same subject, verb and resource for 10 seconds, so a removed binding is effective there after at most that long. workspace-manager and toolchain-manager move to the same check and drop their lists. The rows below for them, and the Organization namespace for muster's MCPServers, are the proposal: today Workspaces all live in `kagent`, toolchain sources are approved per installation, and MCPServers live in muster's namespace.

| Program | Decision | Verb | Resource | Namespace | Needs |
|---|---|---|---|---|---|
| kagent-extensions | may see this agent | get | `agents` (`api.kagent.dev`) | the agent's | user |
| kagent-extensions | may run this agent | create | `sessions` | the agent's | user |
| agent-manager | may deploy or change this agent | create, update, delete | `helmreleases` | the Organization's | editor |
| workspace-manager | may use this Workspace | get | `workspaces` | the Organization's | user |
| workspace-manager | may create a Workspace | create | `workspaces` | the Organization's | editor |
| toolchain-manager | may approve a toolchain source | update | `toolchainsources` | the platform tenant's | editor |
| muster | may write this MCPServer | create, update, delete | `mcpservers` (`muster.giantswarm.io`) | the Organization's | admin |

**Guard.** Anyone who can label a ClusterRole adds rights to an aggregated role. A CI check on the charts refuses rules a capability role must not carry: `get`, `list` or `watch` on Secrets in Organization namespaces, `create` on Pods, `impersonate`, `escalate`, and `bind` outside the capability's own names.

## What this RFC does not do

- Customer `write_all` groups, the `automation` ServiceAccounts, Flux and Crossplane bindings and RoleBindingTemplate stay as they are.
- Workload-cluster RBAC and the KaaS roles (clusters, apps) are not touched. If Shield wants `cluster:*` roles on the same scheme later, that is their RFC.
- No operator is merged. rbac-operator's kubebuilder migration (roadmap#3056) continues as is.
- Observability gets its own RFC from Atlas when it is Organization-shaped.
- Agent and machine identity stays on giantswarm#36698. Until then an agent has exactly the rights of the person who runs it.
- Session shares, workspace grants and Slack thread grants are runtime grants, not membership, and are unchanged.

## Open questions

1. **One operator for the bindings.** Do we agree that the labelled roles and the `bind` list are managed by one operator, with other teams plugging in by shipping labelled ClusterRoles? Which operator that is can be decided separately.
2. **Secrets in a shared Organization namespace.** Admins must create Secrets for their MCP servers in `org-<name>`, but the workload-cluster kubeconfigs and the `automation` ServiceAccount token are there too. RBAC can stop an admin from reading those Secrets, not from getting them mounted into a Pod, for example through an MCPServer that references one by name. And the shipped admin role's write-only Secrets rule is not scoped by name, so an admin can today overwrite or delete the `<cluster>-kubeconfig` Secret in the namespace; the fix for both is the same kind of name-scoping. Routes we see: admission that limits which Secrets an MCPServer or a tenant Pod may reference, by name prefix, which is what the platform already does for EgressPolicies and `tenant-credential-*` Secrets; a separate `org-<name>-agents` namespace, which we would rather avoid so that every capability shares one Organization namespace; or real isolation (kcp), which is more than we can take on now. How would Shield approach it?
3. **Names.** The label keys (`giantswarm.io/capability` and `giantswarm.io/level`?) and whether the three level names are fixed for every capability.

If the answer to 1 is no, or 2 cannot be made safe in the shared namespace, Bumblebee ships its own operator (working name `agent-platform-tenancy-operator`) that creates an `org-<name>-agents` namespace per Organization and manages the three roles and their bindings there. That removes the Secret problem, since no kubeconfig or `automation` ServiceAccount lives in that namespace, and does not wait on rbac-operator. It costs a second definition of an Organization on the management cluster, a second operator to run and secure, duplicated Flux and ServiceAccount wiring per Organization, and the same choice again for every later capability. It is the fallback, not the proposal.

## Alternatives considered

- **A relationship store (OpenFGA or similar).** Rejected in the agent-permissions plan (giantswarm/bumblebee-plans#78): a second source of truth next to Kubernetes RBAC.
- **A members list on the Organization CR.** Rejected: a list people write is a copy of the RoleBindings and needs its own authorizer.
- **A namespace per capability (`org-<name>-agents`).** The fallback above, not the proposal: it solves the Secret question by splitting what an Organization is.

## References

- [Authorization in the platform API](https://docs.giantswarm.io/tutorials/access-management/authorization/)
- [Agent permissions PRD](https://github.com/giantswarm/bumblebee-plans/blob/main/agent-permissions/PRD.md), giantswarm/bumblebee-plans#78
- [Human permissions on agents](https://github.com/giantswarm/giantswarm/issues/36698)
- [rbac-operator migration to kubebuilder](https://github.com/giantswarm/roadmap/issues/3056), [rbac-operator#683](https://github.com/giantswarm/rbac-operator/pull/683)
- Kubernetes: [aggregated ClusterRoles](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#aggregated-clusterroles), [restrictions on role binding creation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#restrictions-on-role-binding-creation-or-update)
- [Miro board](https://miro.com/app/board/uXjVEVa-IFw=): inventory with sources

## Appendix: agent-platform role rules as shipped

From `helm/agent-platform-connectivity/templates/tenants/clusterroles.yaml` on `main`, 2026-10-27. Each level includes the levels below it.

| Role | API group | Resources | Verbs |
|---|---|---|---|
| `agent-platform:platform-user` | `api.kagent.dev` | `agents`, `agenttemplates`, `remotemcpservers`, `modelconfigs` | get, list, watch |
| | `muster.giantswarm.io` | `mcpservers` | get, list, watch |
| | `api.kagent.dev` | `sessions` | create |
| `agent-platform:user` | platform-user, plus `api.kagent.dev` | `egresspolicies` | get, list, watch |
| `agent-platform:editor` | user, plus `helm.toolkit.fluxcd.io` | `helmreleases` | get, list, watch, create, update, patch, delete |
| | `source.toolkit.fluxcd.io` | `ocirepositories` | get, list, watch, create, update, patch, delete |
| | `api.kagent.dev` | `agents`, `agenttemplates`, `remotemcpservers` | create, update, patch, delete |
| | `api.kagent.dev` | `harnesses` | get, list, watch |
| | `""` | `events` | get, list, watch |
| `agent-platform:admin` | editor, plus `api.kagent.dev` | `modelconfigs`, `egresspolicies` | create, update, patch, delete |
| | `""` | `secrets` | create, update, patch, delete (no get, list, watch) |
| | `rbac.authorization.k8s.io` | `rolebindings` | get, list, watch, create, update, patch, delete |
| | `rbac.authorization.k8s.io` | `clusterroles` named `agent-platform:user`, `editor`, `admin` | bind |

To add for this RFC: `muster.giantswarm.io` `mcpservers` write for admin, `workspaces` and toolchain sources per the decision table. The chart values say `tenants.platform.users` binds `agent-platform:user` while the template binds `agent-platform:platform-user`; fixed with the labels.
