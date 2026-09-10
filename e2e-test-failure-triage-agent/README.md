---
creation_date: 2026-05-25
issues:
- https://github.com/giantswarm/roadmap/issues/4303
owners:
- https://github.com/orgs/giantswarm/teams/team-tenet
state: review
summary: Build a service that triages failed E2E test runs. It gathers context from mcp-kubernetes and crust-gather. It uses an LLM to classify each failure, route it to the right team, and create issues or Slack alerts. The work ships in phases. Each phase produces value on its own. We can kill the project at any phase if it stops paying off.
---

# Failure triage and recommendation agent for E2E test runs

## Problem statement

E2E test failures take meaningful engineering time to triage. The release team is small. The work is repetitive. Humans effort may not be the right tool for most of it.

Today:

- Engineers retriage the same kinds of failures over and over. Infra flakes. Known-issue recurrences. Test races. A small set of real bugs hiding in the noise.
- We have no single view of failure trends across suites and providers. We make decisions from incomplete information.
- Rare but customer-critical failures get lost in the volume. They look like common flakes on the surface.
- The first 10-15 minutes of any triage is context-gathering. An automated process could deliver that context in seconds.
- Failures often span the boundary between infrastructure, tests or product code. Infrastructure issues (vcluster, tbot, bootstrap) belong with Tenet. Test or product issues (Ginkgo assertions, controller bugs) belong with provider or app teams. Identifying which team should look at a failure is manual toil today.
- The release team has 1-2 reviewers plus the author. They also carry on-call. Any solution that adds review burden faster than it removes triage burden will fail.

The cost compounds. As the test surface grows, triage burden grows linearly. Team capacity does not.

This RFC integrates the tektoncd/mcp-server evaluation issue. The five ideas in that issue (PR-to-run summarization, daily-suite digest, on-failure issue and Slack creation, infrastructure-vs-test team routing, mc-bootstrap root cause analysis) all fit as use cases of the pipeline proposed here. They are not separate workstreams.

## Decision maker

- Team Tenet
- Team Bumblebee

## Deadline

<TODO: set a deadline, e.g. 2026-06-30. Recommended: 4 weeks from RFC publication to allow stakeholder review without indefinite delay.>

## Who is affected / stakeholders

### Must review and provide feedback before approval

- Release team (owner of the work)
- Tenet (team routing affects them directly; they will receive infrastructure-classified tickets)

### Should review and comment

- Team Phoenix 
- Team Rocket
- Team Tenet 
- Team Shield 

### Informed only

- Engineering leadership — strategic direction on agentic engineering at Giant Swarm
- Other teams considering similar agentic projects — this RFC is intended as a reference pattern

## Preferred solution

We intend to build a small Go service called the the triage service that does the following:

1. Receives a webhook when a Tekton PipelineRun finishes with failed E2E tests.
2. Gathers context for each distinct failure. Two paths. mcp-kubernetes for live or recently-completed runs. crust-gather archives from the OCI registry for runs where the test cluster has been torn down.
3. Calls Claude with the context and a classification schema. The schema covers failure category and team routing.
4. Routes the result deterministically. Infra failure flakes get logged. Test suites failure flakes get low-priority tickets. Enviroment issues get platform tickets. Real bugs caught in our tests get drafted as tickets for human review. Known issues get linked to existing GitHub issues. Unknown cases get Slack notifications to #alert-ci.
5. Persists every event, classification, and feedback in PostgreSQL.
6. Surfaces results through Grafana dashboards, a daily Slack digest in #alert-ci, and a golden set of labeled historical failures that runs as a regression test in CI.
7. Exposes three Slack slash-commands. `/triage pr <repo> <pr-number>`. `/triage daily-digest`. `/triage mc-bootstrap <run-id>`.

### Data access architecture

The service has two paths. It picks the right one based on what's available.

**Path A: mcp-kubernetes for live or recently-completed runs.**

mcp-kubernetes already runs on gazelle-cicdprod. It has proper auth, RBAC, and observability. It exposes Tekton PipelineRuns, TaskRuns, pods, logs, and CRDs.

The `gs-base:e2e-testing` agent skill already encodes how to use this. How to find child runs from a PR. How to follow app fan-out. How to read `run-tests` and `display-results` logs. How to filter by `cicd.giantswarm.io/repo`. The triage service reuses these patterns. It does not reinvent them.

Path A handles:

- The slash-commands. The user is asking about something live or recent.
- The daily digest. Queries `daily-*` PipelineRuns from the last 24 hours.
- mc-bootstrap failures. The MC is long-lived. The relevant state stays queryable.
- Initial failure detection from the webhook. The PipelineRun is still in the system even after the WC is torn down.

**Path B: crust-gather archive from the OCI registry for archived runs.**

When the workload cluster has been torn down, the cluster state is gone. But crust-gather pushed a snapshot to the OCI registry at the moment of failure. The service fetches that snapshot with `oras-go` or `go-containerregistry`. It extracts the slice it needs.

Both paths feed into the same context-assembly stage. The agent does not know or care which source the data came from. It just sees a structured context bundle.

#### crust-gather limitations to know about

crust-gather collection is best-effort. The snapshot has known gaps. The triage service must handle them.

What's excluded:

- **Secrets.** Secret contents are not in snapshots. The agent reasons about symptoms (mount failures, credential errors) without seeing the secret.
- **Lease, EndpointSlice, ControllerRevision.** Accept the gap. Rarely matters for E2E classification.
- **MC Node resources.** MC node-level issues (kubelet failure, taints, node pressure) are not visible. The agent classifies with reduced confidence when these appear involved.
- **Provider controller logs from cluster-scoped MC namespaces.** Maybe excluded. **This needs verification before agent work starts.** If absent, either extend crust-gather config or accept reduced classification accuracy.
- **Post-teardown state.** Snapshots are taken before cluster deletion. If teardown itself fails, there is no second snapshot. The agent is told this and classifies accordingly.

Other constraints:

- **5-minute snapshot window(this is for initial implementation and may be increased based on the need to get more data).** Resources created or deleted outside that window are not captured.
- **Best-effort collection.** If crust-gather fails (network, registry auth), no snapshot exists. The service handles three states: archive present and valid, archive missing, archive present but malformed. Snapshot availability is a tracked operational metric. Target: above 95%.

These are bounds on what the agent can know. Not blockers. We document them upfront so reviewers and future readers see them.


### Pipeline stages

Our flow for agent has six stages. The implementation guide has full detail.

**Stage 1: Intake.**

Tekton CloudEvents webhook fires when a PipelineRun completes. The service filters out cancelled runs and excluded tests. It dedupes by PipelineRun UID. It writes an event row with `state=pending`.

A reconciliation cron runs every 6 hours. It lists recent PipelineRuns via mcp-kubernetes. It cross-references against the event store. It picks up anything the webhook missed. This is a safety net. Push is primary. Reconciliation should pick up zero items most of the time.

**Stage 2: Context assembly.**

For each failure, the service does the following:

1. Parses JUnit XML from Tekton. Extracts test name, provider, suite, stage, error message.
2. Computes the trigger signature/signal. 
3. Gathers cluster state. Path A or Path B depending on the failure.
4. Extracts a curated slice. Events in the namespace during the snapshot window. CAPI conditions. Controller error and warning logs. Node conditions if available.
5. Queries git for commits in the last 7 days that touch files in the stack trace.
6. Queries pgvector for the 3 most similar past failures.
7. Queries the GitHub Issues API for open issues with relevant labels based on past failures.
8. Loads the known-issue catalog. A YAML file in a Giant Swarm repo, mounted as a ConfigMap.
9. Assembles everything into XML-tagged context blocks. Total token budget: around 50k.

Storage. Raw crust gather archives stay in the OCI registry under registry GC. The service extracts a small structured slice (50-200 KB) of valuable insights. That slice is stored in Postgres for long-term retention. This ensures that crust-gather archive growth can be managed based on the registry retention policies. Extracted slices stay forever and feed trend analysis and similarity search.

**Stage 3: Classification.**

The system prompt includes the rubric:

- Infra: vcluster crashloop, tbot, bootstrap, kind→flux→pivot phase indicators
- Test or product: Ginkgo assertions, product code stack traces

<br>

**Exaple of System prompt**
```
When classifying a failure, look for these indicators:

INFRASTRUCTURE indicators (route to Tenet):
- vcluster pods in CrashLoopBackOff or failing to start
- tbot errors, certificate provisioning failures, identity bot logs showing errors
- mc-bootstrap process never completed, or bootstrap script errors
- Log lines or events from kind, flux, or pivot phases showing failure
- Goose or goten errors in setup output

TEST or PRODUCT indicators (route to the provider or app team):
- Ginkgo assertion failures ("Expected X to equal Y", "Timed out waiting for ...")
- Stack traces originating from product code (cluster-api-provider-aws, app-operator, etc.)
- Test logic errors (race conditions in test setup, bad fixture data)

If the evidence shows both, prioritize the EARLIER cause in the failure chain.
For example: if vcluster crashloops AND then a Ginkgo assertion fails because
the cluster isn't reachable, classify as INFRASTRUCTURE — the assertion only
failed because infra was broken.

If no clear indicator from either category, classify as UNKNOWN.

```


The service calls Claude with the context and a stable cached system prompt. The model returns structured JSON:

- `classification`: INFRA_FLAKE | TEST_FLAKE | ENV_CONFIG | REAL_BUG | KNOWN_ISSUE | UNKNOWN
- `confidence`: HIGH | MEDIUM | LOW. Anything below HIGH routes as UNKNOWN.
- `failure_layer`: INFRASTRUCTURE | TEST | PRODUCT | UNKNOWN. This is the routing axis.
- `suggested_team`: tenet | `provider/<name>` | `app/<name>` | unknown. Derived from layer plus CODEOWNERS.
- `evidence`: array of `{source, quote, interpretation}`. Required.
- `issue_link`: `{action: LINK_EXISTING | PROPOSE_NEW | NONE, existing_issue_number?, proposed_title?}`.
- `uncertainty_notes`: what the agent is unsure about.


The prompt also documents the crust-gather limitations. So the agent knows what it can't see.

For REAL_BUG, the same call also produces a draft ticket body. Title. Severity. Repro. Evidence. Implicated commits. Suggested owners. Uncertainty notes.

Every call is traced in Langfuse. Self-hosted on a management cluster.

**Stage 4: Routing.**

Deterministic Go switch. Based on classification, confidence, layer, and suggested team:

- INFRA_FLAKE, HIGH conf, layer=INFRASTRUCTURE → log only, no notification, count in dashboard
- TEST_FLAKE, HIGH conf → create low-priority GitHub issue with `flaky-test` label. Assign to suggested team.
- ENV_CONFIG, HIGH conf, layer=INFRASTRUCTURE → create platform ticket in Tenet's repo
- REAL_BUG, HIGH conf, layer=TEST or PRODUCT → Stage 5. Draft ticket for human review. Route to suggested team.
- KNOWN_ISSUE, HIGH conf → comment on existing GitHub issue
- UNKNOWN, any conf → Slack notification to #alert-ci with the suggested team tagged. Or "team unknown" if classification was below HIGH.

Daily caps prevent bad days from spamming teams:

- 5 new bug tickets per day
- 3 env tickets per day
- 10 flake tickets per day
- 10 Slack notifications per day

Items past the cap queue in the dashboard. They do not fire actions.

### Issue deduplication

Two layers handle deduplication;

**Trigger-level grouping.** Cheap. Happens before any LLM call. Events with the same trigger signature in a 24-hour window are candidate duplicates. The first triggers full investigation. The rest get tentatively linked, pending the first's classification.

**Issue-level grouping.** The agent's job. Given a new event's classification and evidence, it compares against currently-open GitHub issues. It produces one of:

- `LINK_EXISTING` with a specific issue number. When the underlying root cause matches. Triggers an auto-comment with occurrence details.
- `PROPOSE_NEW` with a draft title. When the evidence is genuinely new. Triggers Stage 5.
- `NONE`. When the failure doesn't warrant a ticket.

Human override is one click. A `triage:wrong-link` label re-opens the event for re-classification.

A weekly consistency check looks at the events linked to each open issue. It flags issues where the evidence has diverged significantly. That catches the "same symptom, different root cause" case.

The daily caps are the safety valve. Even if dedup fails badly, dev teams are not flooded.

**Stage 5: Artifact generation.**

For REAL_BUG, the Stage 3 output becomes a GitHub issue. The service creates it in the suggested team's repo. Labels: `agent-drafted, needs-review`. No assignee. Humans assign.

A small Probot watches for `triage:correct` and `triage:incorrect` labels. That's the feedback capture.


**Stage 6: Output and feedback.**

Events, classifications, and feedback persist in Postgres.

Three Grafana dashboards surface system behavior. Operational. Outcomes. Quality.

A daily Tekton cron posts a digest to #alert-ci. It summarizes overnight runs across providers.

Feedback comes in through Slack emoji reactions and GitHub label events.

The golden set is 30-50 hand-labeled historical failures. It lives in a Giant Swarm repo as YAML. It runs in CI as a regression gate on every prompt and model change.

### Slack slash-commands

Three commands. They reuse the same context-assembly and classification logic. The only difference is the trigger.

- `/triage pr <repo> <pr-number>`. Finds the relevant child PipelineRun via mcp-kubernetes. Filters by `cicd.giantswarm.io/repo` and PR labels. Assembles context. Runs the classifier. Posts the summary in-thread.
    
- `/triage daily-digest`. On-demand version of the cron digest. Queries `daily-*` PipelineRuns from the last 24 hours. Summarizes per provider and suite.
    
- `/triage mc-bootstrap <run-id>`. Reads the mc-bootstrap run plus *-vcluster pods plus kubeconfig secrets via mcp-kubernetes. Pinpoints which phase failed.
    
    - `kind`: initial cluster bring-up via goose. Failures show in kind container logs and bootstrap-script output.
    - `flux`: GitOps reconciliation. Failures show in Kustomization and HelmRelease statuses.
    - `pivot`: handover to the management cluster via goten. Failures show in pivot controller logs and the moment-of-handover state.
    - `app`: app deployment after pivot. Failures show in workload pod conditions.

These commands are read-only. Safe to expose broadly.

### Output consolidation

Four output surfaces. No others.

| Output | What it shows |
|---|---|
| Slack #alert-ci | Daily digest, automated notifications, slash-command responses |
| Grafana | Failure trends, classification accuracy, team-routing distribution, snapshot availability, agent latency and cost |
| GitHub Issues | Drafted bug tickets, auto-linked occurrences for known issues, flake tickets. Team assigned from routing. |
| Slack slash-commands | `/triage pr`, `/triage daily-digest`, `/triage mc-bootstrap` |

### Technology stack

| Layer | Choice |
|---|---|
| Agent service | Go |
| LLM provider | Anthropic Claude. Sonnet by default. Opus on escalation. |
| LLM SDK | Anthropic Go SDK. Direct API. No framework. |
| Live cluster data | mcp-kubernetes (already running on gazelle-cicdprod) |
| Archived cluster data | crust-gather via `oras-go` or `go-containerregistry` from the OCI registry |
| Observability | Langfuse. Self-hosted via Helm. |
| Log templating | None in v1. Regex in Go if needed. No Drain3 sidecar. |
| Similarity search | pgvector |
| Event store | PostgreSQL |
| Dashboards | Grafana |
| Notifications | Slack webhooks. #alert-ci. |
| Ticket integration | GitHub Issues API |
| Evaluation | Langfuse evals plus promptfoo for CI regression |
| Trigger | Tekton CloudEvents |

## Build vs. adopt

We build the context assembly logic, the crust-gather extractor, the classification taxonomy and prompt, the routing rules with team mapping, the known-issue catalog, the golden set, and the slash-command handlers. We adopt mcp-kubernetes, Langfuse, pgvector, the Anthropic SDK, and standard Postgres, Grafana, Slack, and GitHub Issues tooling.

## Success criteria

| Phase | Metric | Target |
|---|---|---|
| Week 4 | Classification accuracy on golden set | 70%+ |
| Week 4 | HIGH confidence correct | 85%+ |
| Week 4 | Team-routing accuracy on HIGH confidence | 80%+ |
| Week 4 | Cost per classification | Under $0.05 |
| Month 3 | Engineer hours saved per week | 4+ hours |
| Month 3 | Triage time per failure | 50% reduction from baseline |
| Month 3 | Team-routing precision | 85%+ of auto-routed tickets reach the right team |
| Month 3 | Bugs caught earlier | 3+ confirmed real bugs per quarter caught by the agent |
| Month 6 | Second team adoption | 1+ other team picks up the pipeline |

### Kill criteria

Sunset the project if any of these hold for 4+ consecutive weeks after week 8:

1. Classification accuracy on HIGH confidence drops below 70% and iteration does not recover it.
2. Team-routing precision stays below 75% despite iteration.
3. Cost per classification exceeds $0.50 and tiering doesn't help.
4. Engineer hours saved stays below 2 hours per week despite tuning.
5. False positive rate on draft bug tickets exceeds 30%.
6. Team consistently rates the agent as noise in monthly feedback.
7. No other team is interested in adoption after 6 months.

## Alternative solutions

**Alternative 1: Do nothing.** Continue triaging manually. Rejected. Triage burden compounds as the test surface grows. Team capacity does not.

**Alternative 2: Adopt tektoncd/mcp-server as-is.** Rejected based on colleague evaluation. No auth model. No safety controls. Its informers filter on `app.kubernetes.io/managed-by`, and zero of our PipelineRuns carry that label. mcp-kubernetes already exposes the same data with auth, RBAC, observability, and safety, and it can see our runs filtered by `cicd.giantswarm.io/repo`.

**Alternative 3: Deterministic-only solution (no LLM).** Build the deterministic pipeline (signature clustering, similarity search, dashboards, digest) with no LLM. Partially adopted. Weeks 1-3 deliver exactly this. Rejected as the final state because deterministic logic cannot classify infra vs. test from log content, distinguish same-symptom-different-cause failures, generate human-readable tickets, or adapt to novel failure modes. The hybrid is the answer.

**Alternative 4: Commercial flaky-test product.** Trunk, Datadog CI Visibility, BuildPulse, etc. Rejected. They treat tests as black boxes and classify on pass/fail patterns alone. No awareness of Kubernetes, CAPI, mc-bootstrap phases, or our domain.

**Alternative 5: Agent runs the tests itself.** The original framing of the broader initiative. Rejected. Agents running tests against live clusters add non-determinism on top of existing flakiness. Granting execution rights is a security concern. This RFC covers investigation. Execution is a separate workstream.

**Alternative 6: Multi-agent orchestration from day one.** LangGraph or OpenAI Agents SDK with multiple specialized agents. Rejected for v1. Multi-agent failure modes are harder to debug. A single classification agent with structured output is enough.

**Alternative 7: Drain3 log templating sidecar.** Rejected for v1. New service, new language, permanent operational burden. v1 signatures should be enough. Regex in Go covers 80% of Drain3's value at a fraction of the cost. Drain3 stays on the shelf as a v3+ option only if regex proves insufficient.


## Implementation plan

### Phase 0: Pre-work (week 0)

Before any code:

- Measure baseline triage time. Sample 20 historical failures.
- Hand-label 30 historical failures (classification, layer, team) for the initial golden set.
- Verify that provider controller logs are in the crust-gather snapshot. If absent, extend crust-gather config before code starts.
- Confirm which OCI registry hosts crust-gather archives and what its retention behavior is.
- Confirm Tekton CloudEvents wiring exists or scope the work to add it.
- Map the team-routing taxonomy to specific GitHub teams and repos. Get input from Tenet and provider teams.

### Phase 1: Quick wins (weeks 1-4)

Each week produces something useful on its own.

| Week | Deliverable |
|---|---|
| 1 | Failure data pipeline. Tekton webhook → Postgres event store → bare-bones Grafana dashboard with failure volume, top failing tests, snapshot availability. |
| 2 | Daily digest cron. Queries `daily-*` PipelineRuns via mcp-kubernetes. Posts per-provider summary to #alert-ci. Slash-command stubs for `/triage pr`. |
| 3 | Context bundle artifact. Auto-assembled bundle posted on each failure. |
| 4 | Advisory LLM classification. Langfuse self-hosted. Posted as advisory message in #alert-ci. Purely advisory. No auto-actions. |

At end of week 4, the system is useful with zero auto-actions. If the LLM part is never enabled, the deterministic parts still pay off.

### Phase 2: Auto-routing (weeks 5-12, gated)

Each auto-action turns on only after the corresponding accuracy criterion is met.

| Week | Capability | Gate |
|---|---|---|
| 5-6 | Auto-link KNOWN_ISSUE. Team tagging on Slack notifications. | 95% accuracy on issue-linking and team-routing over 2 weeks |
| 7-8 | Auto-create low-priority TEST_FLAKE tickets. Auto-route to suggested team. | Below 5% false positive rate over 2 weeks |
| 9-10 | Draft bug tickets for REAL_BUG. Full slash-commands with classification. | Engineers report under 5 minutes to review each draft. Under 10% closed as invalid. |
| 11-12 | Auto-issue creation on failure with dedupe. Full feedback loop. | Auto-linking and draft tickets working for 4+ weeks. |

### Phase 3: Sustained value (months 3-6)

The system runs steadily. We measure hours saved, bugs caught earlier, team-routing accuracy, and trust calibration. No new capabilities. Iteration only.

### Phase 4: Adoption (months 6+, conditional)

If v1 meets sustained-value criteria, we document the pattern and expand to other teams.

### Resources needed

- One engineer's primary focus for 12-16 weeks for v1.
- Occasional support from teammates for reviews and golden-set curation.
- LLM budget: $300 per month soft cap for v1. Revisit at month 1.
- Self-hosted Langfuse on a management cluster.
- A dedicated GitHub App for issue creation (higher API rate limits than a personal token).

### Dependencies

- crust-gather pushes snapshots to the OCI registry on failure. Existing behavior.
- mcp-kubernetes runs on gazelle-cicdprod. Existing deployment.
- Tekton CloudEvents available or wired up in Phase 0.
- CODEOWNERS files in relevant repos are current. Team-routing depends on them.

### Risks

| Risk | Mitigation |
|---|---|
| Provider controller logs not in crust-gather snapshot | Verify in Phase 0. Extend crust-gather config or accept reduced accuracy. |
| Team-routing wrong, dev teams lose trust | Advisory mode for 4 weeks before any auto-routing. Team-routing precision is an explicit success and kill criterion. |
| Agent hallucinates evidence | Required evidence array with source, quote, interpretation. Weekly spot-check of 10%. |
| Cost runaway | Hard token budget per invocation. Daily cost ceiling alert. Tiered model usage. |
| Snapshot availability drops | Tracked as an operational signal. Escalates to crust-gather owners independently. |
| Wrong issue auto-linking | One-click reversible by humans. Weekly consistency check. |
| Reviewer fatigue on UNKNOWN | Track unknown rate. Alert if over 20%. Tighten prompt or expand context. |
| Project becomes ambient cost | Explicit kill criteria. Quarterly review. Willingness to sunset. |
| Prompt injection from log content | Treat logs as untrusted. XML-tag context blocks. Bounded classification surface. |
| Webhook drops events silently | Reconciliation cron catches missed events. Pick-up rate is tracked. |

## Communication plan

### Before approval

- Share RFC link with collaborators
- Post the RFC link in #team-tenet with a 2-3 sentence summary.
- Schedule a walkthrough session for stakeholders in our SIG architecture meeting.

### On approval

- Update RFC state from `review` to `approved` in the handbook.
- Announce in #team-tenet and #tenet-chat with the implementation timeline.
- Open the GitHub tracking issue and link it from the RFC, also linking pre-existing issues.

### During implementation

- Weekly written update in #team-tenet: what shipped, what's next, any blockers.
- End-of-phase demos. Phase 1 demo in week 4. Phase 2 demo at week 12.
- Slack post in #alert-ci before any new auto-action turns on, with the gate criteria that were met.

### On phase gates

- Before enabling auto-link in week 5: Slack announcement in #alert-ci. Team-routing precision data shown.
- Before enabling auto-ticket creation in week 7: announcement plus a 1-week opt-out window for any dev team that wants to be excluded initially.
- Before enabling draft bug tickets in week 9: announcement plus opt-in pilot with one provider team before broader rollout.

### Ongoing

- Monthly written feedback survey to the release team (5 minutes).
- Quarterly written status: success metrics, adoption status, kill criteria check, what we learned.

### If killed

- Honest post-mortem in the handbook. What worked. What didn't. What we'd do differently. Captured as a reference for future agentic engineering work.
