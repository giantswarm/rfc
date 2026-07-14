---
creation_date: 2026-07-07
issues: []
owners:
  - https://github.com/orgs/giantswarm/teams/team-bumblebee
  - https://github.com/orgs/giantswarm/teams/team-honeybadger
  - https://github.com/orgs/giantswarm/teams/team-tenet
state: review
summary:
  Defines a harness-neutral contract for app tests so the same test files run under both app-test-suite (fast
  chart tests per PR) and apptest-framework (e2e on workload clusters). One conventional directory per repo,
  test types via build tags or pytest markers, inputs via KUBECONFIG and APP_TEST_* env vars, prerequisite
  controllers declared in .apptest/config.yaml.
---

# The app-testing contract

## Problem

We test our helm charts delivering managed apps using two frameworks: `app-test-suite` (ATS) and
`apptest-framework` (ATF). So far, it was not clear which framework teams should use and how to write the
tests. We propose to keep both frameworks, but specialize them to the two most frequent use cases:

- **app-test-suite (ATS)** - should provide rapid local feedback on PRs and in local dev environments. Its
  goal is to deploy the helm chart under tests as fast as possible and start testing the chart's
  functionality. This means that it will sacrifice all the possible real cluster features to achieve this
  goal. The cluster environment it is meant to run is `kind`, although it doesn't make any assumption about
  the cluster type.
- **apptest-framework (ATF)** takes the opposite approach: it chooses environment realism over the time needed
  to execute the tests. It creates a real workload cluster, installs the chart using the App Platform, and
  runs the full suite, preferably nightly.

With this in mind, it's clear that to provide a comprehensive test coverage and to follow the "fail fast"
principle, we need to use both frameworks.

The trouble is writing the tests. The tests author doesn't want to implement the same or very similar set of
tests twice, once for each framework. The goal of this doc is to propose a test implementation spec that will
allow both ATS and ATF to run the same test suites in their respective environments. Full parity of tests
might not be possible, as test itself might depend on the environment, but we want to get as close as
possible. A local kind cluster is fast but can't do cloud identity, real storage, or upgrades; a workload
cluster can. If a test suite needs to be aware of these differences, the author needs to get the possibility
to gate on the capabilities it needs.

This goal of this RFC is not to dedupe existing tests. It's to define how the two frameworks are different,
what environments they provide and what is the convention that, when respected, can allow to fit both
frameworks with the same test code.

## Decision

### The conventional directory

Tests live in one directory: `tests/app/`. Any harness that deploys the app runs that directory the same way.
Having the directory is the opt-in; there's nothing else to wire up.

It's either one Go module or one Python project, not both. The runner picks the executor from what's there:

- `go.mod`: `go test -mod=readonly -tags=<type>`
- `pyproject.toml`: `uv sync --frozen && uv run pytest -m <type>`
- both, or neither in a non-empty directory: config error, stop.

Dependencies are pinned from committed lockfiles (Go `go.sum`, Python `uv.lock`) and installed with the
network off: the runner sets `GOPROXY=off` alongside `-mod=readonly` (or vendors `tests/app/vendor/`) and runs
`uv sync --frozen --offline`, backed by a pre-warmed module/uv cache. The lockfile flags alone
(`-mod=readonly`, `--frozen`) only freeze resolution, not fetching, so cutting the network is what makes a
missing or stale entry fail loudly instead of quietly downloading. Both runners implement this: under this
contract `tests/app/` is a separate module that atf builds at test time, so atf gains the same fetch point ATS
already has. Same dependency set everywhere, and you can audit it.

An empty `tests/app/` (no module, no project) isn't an opt-in and is skipped.

### Test types

Each test carries one type, set with a Go build tag or a pytest marker. There are three, the same ones ATS
already has:

| Type         | Runs                           | What it is                                   |
| ------------ | ------------------------------ | -------------------------------------------- |
| `smoke`      | normal flow, first             | quick sanity checks                          |
| `functional` | normal flow, after smoke       | full feature tests                           |
| `upgrade`    | upgrade flow, before and after | checks the app still works across an upgrade |

`upgrade` is its own type, not a flag on the others. The upgrade flow doesn't re-run smoke and functional; it
runs the `upgrade` tests, once on the old version (`APP_TEST_UPGRADE_STAGE=pre`) and once after upgrading
(`=post`). The pre run is the baseline: if it passes and post fails, the upgrade caused it, not something that
was already broken.

Most upgrade checks are symmetric ("the app answers") and assert the same thing both times. When some state
has to survive the upgrade, either seed it in the `pre-upgrade` hook and check it in the post run, or keep it
in one test that branches on the stage:

```go
if os.Getenv("APP_TEST_UPGRADE_STAGE") != "post" {
    t.Skip("verification runs after the upgrade")
}
```

Seeding is a side effect, so it's a hook; checking is an assertion, so it's a test. Upgrade tests and the
`pre-upgrade` hook also get `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION`.

### Hooks

Hooks do things with side effects (install a prerequisite, create a pod, clean up); tests check things.
Splitting them is what lets the upgrade flow seed state without re-running a suite. Like tests, setup and
teardown are per-app and get duplicated across harnesses, so the contract makes them portable too: optional
executables in `tests/app/`, run with the same environment as tests.

| Hook                          | Runs                                                                                                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/app/hooks/setup`       | after the cluster is ready, before the app is deployed (for example: install prerequisites)                                                                        |
| `tests/app/hooks/pre-upgrade` | upgrade flow only: after the previous version is deployed, before the upgrade (for example: create a pod or write a record an `upgrade` test then checks survived) |
| `tests/app/hooks/teardown`    | after all tests, before the harness tears anything down (for example: clean up external resources)                                                                 |

A hook is any executable at that path: a script with a shebang or a built binary, run directly (not sourced).
It runs out of process, so the one-language rule doesn't apply and you can write it in whatever fits. Keep it
small; anything bigger is a test or a harness-native hook.

A missing hook does nothing. A non-zero exit fails the run. Hooks gate on the environment like category-2
tests do; `pre-upgrade` also gets the from/to versions.

Convention discovery of those three paths is the default, and every runner has to implement it. That's the
zero-wiring part. A harness can also keep its own hook flags, so existing repos don't have to move and
harness-specific hooks still work. If a flag and a convention file point at the same contract hook, the runner
stops (same as finding both `go.mod` and `pyproject.toml`), so migrating is "add the file, drop the flag" in
one commit rather than running both. Only the convention path is guaranteed and checked by the conformance
suite; the flags are each harness's own business.

How the three points map today:

| Contract hook            | ATS                                                                  | atf                                       |
| ------------------------ | -------------------------------------------------------------------- | ----------------------------------------- |
| `setup` (before deploy)  | new pre-deploy point (its `--app-tests-pre-hook` fires after deploy) | `AfterClusterReady` (runs before install) |
| `pre-upgrade`            | `--upgrade-tests-upgrade-hook` at `ATS_HOOK_STAGE=pre_upgrade`       | `BeforeUpgrade`                           |
| `teardown` (after tests) | `--app-tests-post-hook`                                              | suite callback                            |

A runner covers each point with either the file or the flag, not both. Anything not in that table (ATS's
`post_upgrade` stage, its pre/post test hooks) stays harness-native.

Same boundary as tests: a hook only gets the app cluster's `KUBECONFIG`. Anything that needs harness internals
(MC access, the App CR, framework state) stays in a harness-native hook: ATS's config hooks for points we
don't cover, or atf's `AfterClusterReady` / `BeforeUpgrade`.

### Prerequisite controllers

Some apps under test create custom resources — a Flux `Kustomization`, an Argo `Application`, an
`ExternalSecret` — that do nothing until a controller is running to reconcile them. Only some apps need any
given controller, and installing one is expensive, so the app declares the controllers it needs and the runner
bootstraps exactly those before the app is deployed. There's no auto-detection: declaring is the opt-in, the
same rule as everything else here.

This is the declarative sibling of the `setup` hook. `setup` runs an app-specific script; a controller names
something the runner already knows how to install. The declaration is shared, but the provider code that
installs a named controller is each harness's own — a harness targeting kind and one targeting a workload
cluster install it differently — so a controller only works on a harness that has a provider registered for
that name.

Controllers are declared in the shared `.apptest/config.yaml` (see Shared configuration):

```yaml
controllers:
  - name: flux
    semver: ">=2.0.0 <3.0.0"
    harness:
      - name: ats
        valuesFile: flux-small.yaml
      - name: atf
        valuesFile: flux-full.yaml
  - name: external-secrets
    semver: "0.x"
```

- `name` (required): the controller's harness-neutral id. If the running harness has no provider registered
  for it, the run fails.
- `semver` (required): a version range with Masterminds/semver v3 semantics (the same Flux `OCIRepository` and
  Helm `--version` use), resolved to the highest version that satisfies it.
- `harness` (optional): per-harness install values files, listed by harness name rather than keyed by it, so
  the neutral file stays a list you extend, not a map with harness names baked into its shape. Each
  `valuesFile` ends in `.yaml`, sits beside `config.yaml` under `.apptest/`, and layers over the controller's
  defaults. No entry for the running harness means defaults; a named file that's missing or not `.yaml` fails
  the run.

Order matters: controllers install in list order, each fully ready before the next, so one that depends on
another goes after it. They install once per run and are shared across every type and both flows — a
prerequisite is run infrastructure, not something per test.

An already-present controller is reused. The runner checks the installed version: absent, it installs; present
and within `semver`, it leaves it alone; present but outside `semver`, the run fails. The runner never
upgrades, downgrades, or removes a controller it finds — the cluster may not be ours, and leaving controllers
in place is also what makes the next run on the same cluster faster. A provider may run its own pre-install
and post-install steps (create RBAC, wait for a webhook or a CRD to establish) around the install.

Controllers are not capabilities. `APP_TEST_CAPABILITIES` is what a cluster already provides and a test gates
on; a controller is something the runner adds to any cluster. When a bootstrapped controller is a gitops
engine, the runner surfaces which one through `APP_TEST_EXTRA_GITOPS_ENGINE`.

### Inputs

Tests get everything from the environment. They don't provision anything: no clusters, no chart installs, no
App CRs.

| Variable                                                        | Required          | Meaning                                                                                                                                                                                                                                 |
| --------------------------------------------------------------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `KUBECONFIG`                                                    | yes               | kubeconfig of the cluster the app is deployed on (never the MC)                                                                                                                                                                         |
| `APP_TEST_TYPE`                                                 | yes               | the type currently being run                                                                                                                                                                                                            |
| `APP_TEST_RELEASE_NAME`                                         | yes               | Helm release name of the app under test                                                                                                                                                                                                 |
| `APP_TEST_RELEASE_NAMESPACE`                                    | yes               | namespace the app is deployed into                                                                                                                                                                                                      |
| `APP_TEST_CHART_VERSION`                                        | yes               | version of the chart under test                                                                                                                                                                                                         |
| `APP_TEST_CLUSTER_TYPE`                                         | yes               | topology of the cluster the app runs on: `kind` (local single-node), `capi` (a CAPI workload cluster), or `external` (a cluster the runner did not provision). Describes shape, not capability; gate on `APP_TEST_CAPABILITIES` instead |
| `APP_TEST_CAPABILITIES`                                         | yes               | comma-separated capabilities the cluster actually provides, e.g. `cloud-identity,persistent-storage,load-balancer`; empty is valid. The runner sets it from what it provisioned or was handed. This is what a test gates on             |
| `APP_TEST_KUBERNETES_VERSION`                                   | optional          | Kubernetes server version                                                                                                                                                                                                               |
| `APP_TEST_VALUES_FILE`                                          | optional          | values file the app was deployed with                                                                                                                                                                                                   |
| `APP_TEST_UPGRADE_STAGE`                                        | upgrade flow only | `pre` or `post`: which side of the upgrade this `upgrade`-type run is on                                                                                                                                                                |
| `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION` | upgrade flow only | versions on either side of the upgrade; available to the `pre-upgrade` hook and `upgrade`-typed tests                                                                                                                                   |
| `APP_TEST_EXTRA_*`                                              | optional          | harness extras, for example `APP_TEST_EXTRA_GITOPS_ENGINE`                                                                                                                                                                              |

The prefix is `APP_TEST_`, which reads the same under either harness. ATS publishes these under the old `ATS_`
prefix today. Where a name maps straight across (`ATS_X` to `APP_TEST_X`, e.g. `ATS_RELEASE_NAME`,
`ATS_CHART_VERSION`, `ATS_CLUSTER_TYPE`, `ATS_EXTRA_*`) the runner exports both, so nothing breaks and new
tests use `APP_TEST_`. Dual export isn't free (two names to know and grep for), so `ATS_` is deprecated and
will be removed in a later change once repos have migrated.

Four names are renamed, because the old ones were unclear or, for the upgrade stage, were never test-facing
under one name to begin with:

| Legacy                                                            | Canonical                     | Note                                                                                                                                                                 |
| ----------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ATS_TEST_TYPE`                                                   | `APP_TEST_TYPE`               | straight rename                                                                                                                                                      |
| `ATS_APP_CONFIG_FILE_PATH`                                        | `APP_TEST_VALUES_FILE`        | straight rename                                                                                                                                                      |
| `ATS_CLUSTER_VERSION`                                             | `APP_TEST_KUBERNETES_VERSION` | straight rename                                                                                                                                                      |
| `ATS_EXTRA_UPGRADE_TEST_STAGE` (tests) / `ATS_HOOK_STAGE` (hooks) | `APP_TEST_UPGRADE_STAGE`      | value also changes: `pre_upgrade`/`post_upgrade` become `pre`/`post`. The runner does not alias the value, so existing upgrade tests reading the old one must update |

`ATS_CHART_PATH` and `ATS_TEST_DIR` have no `APP_TEST_` equivalent; the contract doesn't expose them and they
stay ATS-only. `APP_TEST_CAPABILITIES` is new, computed by the runner, with no `ATS_` predecessor.
`KUBECONFIG` stays as-is; it's the standard name, not ours.

### Runner guarantees

Before the tests run, a conforming runner makes sure:

1. the controllers declared in `.apptest/config.yaml`, if any, are bootstrapped and ready, once per run,
   before anything is deployed,
2. the `setup` hook ran, if present, after the controllers were ready and before the app was deployed,
3. the app is deployed and settled: each runner first waits on its own mechanism signal (ATS: Helm release
   installed, or via a GitOps engine; atf: App CR at `deployed`), then on the shared gate `IsReleaseReady`
   (the release's workloads Available) before any test runs,
4. the required variables are exported,
5. the `teardown` hook runs, if present, after the last test type and before the harness's own teardown.

Normal flow: run `smoke`, then `functional`. Upgrade tests don't run here.

Upgrade flow (any `upgrade` tests collected): install the previous version and let it settle, run `upgrade`
tests with `APP_TEST_UPGRADE_STAGE=pre`, run the `pre-upgrade` hook, upgrade and let it settle, run `upgrade`
tests with `=post`. smoke and functional don't run here.

"No tests of this type" passes rather than fails (Go excludes all files via build tags; pytest exits 5), since
a repo may only have some types. It isn't silent, though: the runner reports how many tests it collected per
type, so a mistyped tag (also zero) shows up instead of going green. Repos that want it strict list their
expected types in `.apptest/config.yaml`; a listed type with zero tests fails. Results come out as junit XML
(`gotestsum --junitfile`, `pytest --junitxml`).

### Cadence and feedback latency

The PR cluster often lacks cloud identity, real storage, or load balancers, so tests that need those
capabilities only run nightly on a workload cluster. Their result isn't tied to the PR that caused it: a PR
can break a cloud-only path, pass PR CI, and fail that night against a batch of other commits.

We accept that, but two things keep it from being a silent trap:

1. A nightly-only test is a choice you can see. A test that gates on a capability the PR cluster lacks
   (category 2) is invisible per-PR by design; the skip shows by name and the collected counts show it didn't
   run, so it doesn't read as coverage it isn't.
2. You can pull the nightly flow forward. `/run` triggers the workload-cluster flow on a PR, so a cloud-path
   change can get its result now instead of that night.

Gate on the capability you need (`APP_TEST_CAPABILITIES`), never on cluster type or harness (see
Harness-specific tests): a test that needs cloud identity runs anywhere advertising `cloud-identity`, whether
that's the nightly WC or a provided cluster that happens to have it.

### Shared configuration

Test _code_ lives in `tests/app/`; shared _declarations_ live in `.apptest/`. `.apptest/config.yaml` holds
only what both harnesses need, and the controller values files (see Prerequisite controllers) sit beside it:

```yaml
installNamespace: kube-system
expectedTypes: [smoke, functional, upgrade] # optional: types that must collect at least one test
controllers: [...] # optional: see Prerequisite controllers
```

The upgrade flow is inferred, not configured: if the runner collects any `upgrade`-typed tests it runs the
upgrade flow, otherwise it doesn't. Same presence-is-the-opt-in rule as the directory and the other types, so
there's no separate switch to keep in sync. Each harness still learns which version to upgrade from through
its own config (ATS's stable-app settings, atf's latest published release); that part is harness-specific, not
contract.

The one lint: a type in `expectedTypes` that collects zero tests fails the run. `expectedTypes` is optional;
leave it out to keep the "no tests is fine" default. It's also how you make a type mandatory. List `upgrade`,
and a typo'd tag (which collects zero) fails instead of quietly skipping the flow.

Everything harness-specific stays in that harness's config: `.ats/main.yaml` (cluster types, catalogs,
executor options) and `tests/e2e/config.yaml` (appCatalog, providers, MC options). Values files stay
per-harness too; a kind cluster and a workload cluster legitimately want different values, and each harness
loads them its own way.

### Harness-specific tests

The contract is for the common case. Where a test goes:

1. Checks the deployed app, works anywhere: `tests/app/`, no gate. Most tests.
2. Checks the deployed app but needs a capability not present everywhere: `tests/app/` with a runtime skip on
   the capability, for example `if !slices.Contains(caps, "cloud-identity") { t.Skip(...) }` where `caps`
   comes from `APP_TEST_CAPABILITIES`. Skips still show by name.
3. Needs harness machinery (MC access, bundle installs, AWS/IRSA, cluster manipulation): a normal atf suite
   under `tests/e2e/suites/`, which this RFC doesn't touch.

So a repo can hold two Go modules: `tests/app/` (portable) and `tests/e2e/` (atf-native), each with its own
`go.mod`. They're separate on purpose, since the portable one has to build without atf's dependencies. If you
want one toolchain over both, add a `go.work` at the repo root; it's optional and never part of the contract.

Gate on what the contract tells you about the environment, never on which harness is running. If a test needs
to know the harness name, it's category 3.

Gate on `APP_TEST_CAPABILITIES`, not on `APP_TEST_CLUSTER_TYPE`, and never on the harness. Cluster type is
topology, not capability: `kind` usually being the PR runner and `capi` usually being the nightly one is a
coincidence, and ATS moving to provided clusters
([app-test-suite#675](https://github.com/giantswarm/app-test-suite/pull/675)) breaks even that, since the PR
runner can then be handed a cluster with cloud identity. Check the capability you actually need, so any
cluster that advertises it, including an `external` one, passes the same gate. If what you need isn't a
declared capability, the test needs harness machinery, which is category 3.

### Conformance and ownership

Two runners, one contract, so they'll drift unless something checks. The contract ships a conformance suite: a
fixture (trivial app, one test per type, a hook, a declared controller, a lockfile) and assertions on the env
vars, ordering, exit codes, controller bootstrap, and lints above. A runner conforms only if it passes the
suite in CI; ATS and atf both wire it in. New guarantees go into the suite in the same PR that adds them here.

Passing per runner isn't enough: both can pass and still disagree on what a test sees, which is the drift that
hurts (a smoke test that's green on PR and flaky at night). So the suite also checks parity: the same fixture
through both runners has to bootstrap the same controllers, collect the same counts, and end with the same
result, or the suite fails. The known trap is guarantee 2, "settled": ATS gets there when the Helm release
reports installed, atf when the App CR reads `deployed`, and those aren't the same moment. The contract pins
the observable, not the mechanism: settled means every workload the release created is ready, not that a
status field flipped. `clustertest.wait.IsReleaseReady(name, namespace)` is the shared definition. It reuses
clustertest's existing `AreAll*Ready` conditions rather than reimplementing readiness; the only thing missing
today is scope, since those list cluster-wide, so they gain a label-selector argument and `IsReleaseReady`
ANDs them over the release's objects (`app.kubernetes.io/instance=<name>`): Deployments, StatefulSets and
DaemonSets Available, Jobs succeeded. Scoping matters because a workload cluster runs far more than the app
under test, so an unscoped "all ready" would both stall on unrelated workloads and make the two runners
observe different sets. Each runner still waits on its own mechanism signal (Helm `installed`, App CR
`deployed`) first; `IsReleaseReady` is the common gate on top, and the parity fixture checks that neither
runner starts tests before it holds.

team-tenet owns the contract: this doc, the suite, and the call when the runners disagree. team-honeybadger
owns ATS, team-bumblebee owns atf. Changing the contract is a PR here that updates the suite. A runner lagging
is a bug in that runner, not a reason to fork.

## Implementation

- **apptest-framework** gets a convention-runner: after the workload cluster and App CR are up, it grabs the
  WC kubeconfig (`framework.MC().GetClusterKubeConfig(ctx, name, namespace)` on the clustertest MC client),
  writes it out, exports the env contract, picks the executor, and runs it per type. For upgrades it adds the
  pre run. Today it runs the suite once after the upgrade; now it also runs `upgrade` tests against the old
  version first (`APP_TEST_UPGRADE_STAGE=pre`). `BeforeUpgrade` maps to the `pre-upgrade` hook. The image adds
  `uv` and `gotestsum`. In-process suites are untouched. Two things make this cheap: Ginkgo runs under plain
  `go test`, and pytest tests built on pytest-helm-charts already read `KUBECONFIG`, so existing ATS tests in
  either language run on workload clusters as-is.
- **app-test-suite** exports the `APP_TEST_*` names next to the old `ATS_*` ones. It already runs `upgrade`
  tests both before and after the upgrade, so `APP_TEST_UPGRADE_STAGE` is a rename of the stage it already
  tracks (`ATS_EXTRA_UPGRADE_TEST_STAGE`), with the value normalized to `pre`/`post`. It keeps its hook flags
  and also discovers the convention hooks by path (stopping if a flag and a file point at the same one), and
  adds a pre-deploy point for `setup`. Its `--app-tests-pre-hook` runs after deploy, so `setup` is a new call
  between `_ensure_cluster_prerequisites` and the install. It looks in `tests/app/` as well as today's
  `tests/ats/`, reads the shared `.apptest/config.yaml`, and emits junit via gotestsum. Its upgrade pre/post
  behavior doesn't change. Its TEST_CONTRACT.md becomes a pointer here plus ATS-specific detail.
- **clustertest**: the existing `AreAll*Ready` conditions gain an optional label-selector argument (matching
  the style of `AreNumNodesReady`, which already takes `listOptions`), and a thin
  `wait.IsReleaseReady(name, namespace)` ANDs them over `app.kubernetes.io/instance=<name>`. No new readiness
  logic; both runners and the atf-native suites share one definition of ready, and the parity check has one
  thing to assert against.
- **controllers**: both runners parse `.apptest/config.yaml`'s `controllers` and bootstrap them before deploy
  — detect, install the `semver`-selected version if absent, fail if a present one is out of range, wait until
  ready. The declaration is shared; the provider that installs a given controller name is per-harness. ATS
  lands the provider framework first and syncs its existing providers in after, so until then a declared
  controller fails as "unknown controller", which is the contract's behaviour for an unregistered name.
- **the on-demand trigger**: the workload-cluster pipeline runs on `/run` against a PR, not just nightly, so a
  cloud-path change can get its result without waiting.
- **the conformance suite** lives here with the RFC: the fixture app and the assertions, parity check
  included. Both runners run it in CI; it's what "conforms" means.
- **devctl `gen apptest` and template-app** scaffold the layout for new repos.
- Migration happens as repos get touched; no flag day. Pilot:
  [giantswarm/muster#954](https://github.com/giantswarm/muster/pull/954).

## Alternatives considered

- **A shared assertions library both harnesses import per repo.** Tried it in muster; the module, replace
  directives, and adapter code guarded about a dozen lines of predicate per repo. Not worth it; better to
  align the runners so the test files themselves are shared.
- **Standardize on Ginkgo.** Ginkgo runs under `go test`, so it's allowed, but requiring it would shut out the
  pytest repos and tie the contract to a framework for nothing. We standardize selection and inputs, not the
  framework.
- **A `values: {ats: ..., e2e: ...}` map for the app's deploy values.** No: the app's values are
  harness-specific (a kind and a workload cluster want different ones) and stay in each harness's own config,
  not the neutral file — that would be the config version of gating a test on the harness. The `controllers`
  section is the bounded exception: it names per-harness values files, but as a `harness` list (the name is a
  field, not a map key) and only for runner-bootstrapped infrastructure, not the app.
- **One runner with two modes instead of two behind a contract.** One runner covering kind and workload
  clusters wouldn't need a contract at all. But the two modes line up with two mature codebases owned by two
  teams (ATS/honeybadger, atf/tenet), each with provisioning and pipeline code the other doesn't want. Merging
  them is a bigger, riskier job than aligning their edges, and the parity check gets most of the anti-drift
  value for far less. Revisit if the runners keep drifting.
