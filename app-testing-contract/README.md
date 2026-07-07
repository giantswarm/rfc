---
creation_date: 2026-07-07
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-bumblebee
- https://github.com/orgs/giantswarm/teams/team-honeybadger
- https://github.com/orgs/giantswarm/teams/team-tenet
state: review
summary: Defines a harness-neutral contract for app tests so the same test files run under both app-test-suite (chart tests on kind) and apptest-framework (e2e on workload clusters). One conventional directory per repo, test types via build tags or pytest markers, inputs via KUBECONFIG and APP_TEST_* env vars.
---

# The app-testing contract

## Problem

We test managed apps two ways, and we want to keep both:

- **app-test-suite (ATS)** installs the chart on a kind cluster and runs
  quick checks on every PR.
- **apptest-framework (atf)** creates a real workload cluster, installs the
  App CR, and runs the full suite nightly.

kind is fast but can't do cloud identity, real storage, or upgrades; the
workload cluster can. So the two are a fast/slow pair, not duplicates.

The trouble is writing the tests. ATS wants pytest or plain Go; atf wants
Ginkgo. To cover both you write the same check twice in two styles, so most
repos write it for one harness or skip it. Almost nobody has both, and the
people stuck on one aren't happy about it.

This RFC doesn't dedupe existing tests; there aren't many to dedupe, for
the reason above. It makes the two harnesses agree on how tests are written
and run, so you write a check once and both run it: the kind-compatible
part on every PR, everything nightly.

ATS already has a test contract
([docs/TEST_CONTRACT.md](https://github.com/giantswarm/app-test-suite/blob/master/docs/TEST_CONTRACT.md)),
but it lives in the ATS repo and only ATS follows it. We lift it out, make
it harness-neutral, and make atf follow it too. It stays independent of any
test framework or language.

## Decision

### The conventional directory

Tests live in one directory: `tests/app/`. Any harness that deploys the app
runs that directory the same way. Having the directory is the opt-in;
there's nothing else to wire up.

It's either one Go module or one Python project, not both. The runner picks
the executor from what's there:

- `go.mod`: `go test -mod=readonly -tags=<type>`
- `pyproject.toml`: `uv sync --frozen && uv run pytest -m <type>`
- both, or neither in a non-empty directory: config error, stop.

Dependencies are pinned and installed offline: Go from a committed `go.sum`
(`-mod=readonly`), Python from a committed `uv.lock` (`--frozen`). No runner
resolves versions from the network at test time; a missing or stale
lockfile fails instead of quietly fetching. Same dependency set everywhere,
and you can audit it.

An empty `tests/app/` (no module, no project) isn't an opt-in and is
skipped.

### Test types

Each test carries one type, set with a Go build tag or a pytest marker.
There are three, the same ones ATS already has:

| Type | Runs | What it is |
|---|---|---|
| `smoke` | normal flow, first | quick sanity checks |
| `functional` | normal flow, after smoke | full feature tests |
| `upgrade` | upgrade flow, before and after | checks the app still works across an upgrade |

`upgrade` is its own type, not a flag on the others. The upgrade flow
doesn't re-run smoke and functional; it runs the `upgrade` tests, once on
the old version (`APP_TEST_UPGRADE_STAGE=pre`) and once after upgrading
(`=post`). The pre run is the baseline: if it passes and post fails, the
upgrade caused it, not something that was already broken.

Most upgrade checks are symmetric ("the app answers") and assert the same
thing both times. When some state has to survive the upgrade, either seed it
in the `pre-upgrade` hook and check it in the post run, or keep it in one
test that branches on the stage:

```go
if os.Getenv("APP_TEST_UPGRADE_STAGE") != "post" {
    t.Skip("verification runs after the upgrade")
}
```

Seeding is a side effect, so it's a hook; checking is an assertion, so it's
a test. Upgrade tests and the `pre-upgrade` hook also get
`APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION`.

### Hooks

Hooks do things with side effects (install a prerequisite, create a pod,
clean up); tests check things. Splitting them is what lets the upgrade flow
seed state without re-running a suite. Like tests, setup and teardown are
per-app and get duplicated across harnesses, so the contract makes them
portable too: optional executables in `tests/app/`, run with the same
environment as tests.

| Hook | Runs |
|---|---|
| `tests/app/hooks/setup` | after the cluster is ready, before the app is deployed (for example: install prerequisites) |
| `tests/app/hooks/pre-upgrade` | upgrade flow only: after the previous version is deployed, before the upgrade (for example: create a pod or write a record an `upgrade` test then checks survived) |
| `tests/app/hooks/teardown` | after all tests, before the harness tears anything down (for example: clean up external resources) |

A hook is any executable at that path: a script with a shebang or a built
binary, run directly (not sourced). It runs out of process, so the
one-language rule doesn't apply and you can write it in whatever fits. Keep
it small; anything bigger is a test or a harness-native hook.

A missing hook does nothing. A non-zero exit fails the run. Hooks gate on
the environment like category-2 tests do; `pre-upgrade` also gets the
from/to versions.

Convention discovery of those three paths is the default, and every runner
has to implement it. That's the zero-wiring part. A harness can also keep
its own hook flags, so existing repos don't have to move and
harness-specific hooks still work. If a flag and a convention file point at
the same contract hook, the runner stops (same as finding both `go.mod` and
`pyproject.toml`), so migrating is "add the file, drop the flag" in one
commit rather than running both. Only the convention path is guaranteed and
checked by the conformance suite; the flags are each harness's own business.

How the three points map today:

| Contract hook | ATS | atf |
|---|---|---|
| `setup` (before deploy) | new pre-deploy point (its `--app-tests-pre-hook` fires after deploy) | `AfterClusterReady` (runs before install) |
| `pre-upgrade` | `--upgrade-tests-upgrade-hook` at `PRE_UPGRADE` | `BeforeUpgrade` |
| `teardown` (after tests) | `--app-tests-post-hook` | suite callback |

A runner covers each point with either the file or the flag, not both.
Anything not in that table (ATS's `POST_UPGRADE`, its pre/post test hooks)
stays harness-native.

Same boundary as tests: a hook only gets the app cluster's `KUBECONFIG`.
Anything that needs harness internals (MC access, the App CR, framework
state) stays in a harness-native hook: ATS's config hooks for points we
don't cover, or atf's `AfterClusterReady` / `BeforeUpgrade`.

### Inputs

Tests get everything from the environment. They don't provision anything:
no clusters, no chart installs, no App CRs.

| Variable | Required | Meaning |
|---|---|---|
| `KUBECONFIG` | yes | kubeconfig of the cluster the app is deployed on (never the MC) |
| `APP_TEST_TYPE` | yes | the type currently being run |
| `APP_TEST_RELEASE_NAME` | yes | Helm release name of the app under test |
| `APP_TEST_RELEASE_NAMESPACE` | yes | namespace the app is deployed into |
| `APP_TEST_CHART_VERSION` | yes | version of the chart under test |
| `APP_TEST_CLUSTER_TYPE` | yes | cluster the app runs on: `kind` (local single-node, no cloud), `capi` (a CAPI workload cluster with cloud identity), or `external` (a pre-existing cluster the runner did not provision) |
| `APP_TEST_KUBERNETES_VERSION` | optional | Kubernetes server version |
| `APP_TEST_VALUES_FILE` | optional | values file the app was deployed with |
| `APP_TEST_UPGRADE_STAGE` | upgrade flow only | `pre` or `post`: which side of the upgrade this `upgrade`-type run is on |
| `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION` | upgrade flow only | versions on either side of the upgrade; available to the `pre-upgrade` hook and `upgrade`-typed tests |
| `APP_TEST_EXTRA_*` | optional | harness extras, for example `APP_TEST_EXTRA_GITOPS_ENGINE` |

The prefix is `APP_TEST_`, which reads the same under either harness. ATS
publishes these under the old `ATS_` prefix today; runners export both so
nothing breaks, and new tests use `APP_TEST_`. Dual export isn't free (two
names to know and grep for), so `ATS_` is deprecated and will be removed in
a later change once repos have migrated. Most names map straight across
(`ATS_X` to `APP_TEST_X`);
three are renamed because the old names were unclear:

| Legacy | Canonical |
|---|---|
| `ATS_TEST_TYPE` | `APP_TEST_TYPE` |
| `ATS_APP_CONFIG_FILE_PATH` | `APP_TEST_VALUES_FILE` |
| `ATS_CLUSTER_VERSION` | `APP_TEST_KUBERNETES_VERSION` |

`KUBECONFIG` stays as-is; it's the standard name, not ours.

### Runner guarantees

Before the tests run, a conforming runner makes sure:

1. the `setup` hook ran, if present, after the cluster was ready and before
   the app was deployed,
2. the app is deployed and settled (ATS: Helm release installed, or via a
   GitOps engine; atf: App CR at `deployed`),
3. the required variables are exported,
4. the `teardown` hook runs, if present, after the last test type and before
   the harness's own teardown.

Normal flow: run `smoke`, then `functional`. Upgrade tests don't run here.

Upgrade flow (any `upgrade` tests collected): install the previous version
and let it settle, run `upgrade` tests with `APP_TEST_UPGRADE_STAGE=pre`, run the
`pre-upgrade` hook, upgrade and let it settle, run `upgrade` tests with
`=post`. smoke and functional don't run here.

"No tests of this type" passes rather than fails (Go excludes all files via
build tags; pytest exits 5), since a repo may only have some types. It isn't
silent, though: the runner reports how many tests it collected per type, so
a mistyped tag (also zero) shows up instead of going green. Repos that want
it strict list their expected types in `config.yaml`; a listed type with
zero tests fails. Results come out as junit XML (`gotestsum --junitfile`,
`pytest --junitxml`).

### Cadence and feedback latency

kind can't do cloud identity, storage, or load balancers, so tests that
need those only run nightly. Their result isn't tied to the PR that caused
it: a PR can break a cloud-only path, pass PR CI, and fail that night
against a batch of other commits.

We accept that, but two things keep it from being a silent trap:

1. A nightly-only test is a choice you can see. Gating a test off kind
   (category 2) makes it invisible per-PR by design; the skip shows by name
   and the collected counts show it didn't run, so it doesn't read as
   coverage it isn't.
2. You can pull the nightly flow forward. `/run` triggers the
   workload-cluster flow on a PR, so a cloud-path change can get its result
   now instead of that night.

Where you can, gate on the capability you need rather than kind-vs-WC (see
Harness-specific tests): a test that needs cloud identity also runs on an
`external` cluster that has it.

### Shared configuration

`tests/app/config.yaml` holds only what both harnesses need:

```yaml
installNamespace: kube-system
expectedTypes: [smoke, functional, upgrade]   # optional: types that must collect at least one test
```

The upgrade flow is inferred, not configured: if the runner collects any
`upgrade`-typed tests it runs the upgrade flow, otherwise it doesn't. Same
presence-is-the-opt-in rule as the directory and the other types, so there's
no separate switch to keep in sync. Each harness still learns which version
to upgrade from through its own config (ATS's stable-app settings, atf's
latest published release); that part is harness-specific, not contract.

The one lint: a type in `expectedTypes` that collects zero tests fails the
run. `expectedTypes` is optional; leave it out to keep the "no tests is
fine" default. It's also how you make a type mandatory. List `upgrade`, and
a typo'd tag (which collects zero) fails instead of quietly skipping the
flow.

Everything harness-specific stays in that harness's config: `.ats/main.yaml`
(cluster types, catalogs, executor options) and `tests/e2e/config.yaml`
(appCatalog, providers, MC options). Values files stay per-harness too; a
kind cluster and a workload cluster legitimately want different values, and
each harness loads them its own way.

### Harness-specific tests

The contract is for the common case. Where a test goes:

1. Checks the deployed app, works anywhere: `tests/app/`, no gate. Most
   tests.
2. Checks the deployed app but only makes sense in one environment:
   `tests/app/` with a runtime skip, for example
   `if os.Getenv("APP_TEST_CLUSTER_TYPE") != "kind" { t.Skip(...) }`. Skips
   still show by name.
3. Needs harness machinery (MC access, bundle installs, AWS/IRSA, cluster
   manipulation): a normal atf suite under `tests/e2e/suites/`, which this
   RFC doesn't touch.

So a repo can hold two Go modules: `tests/app/` (portable) and `tests/e2e/`
(atf-native), each with its own `go.mod`. They're separate on purpose, since
the portable one has to build without atf's dependencies. If you want one
toolchain over both, add a `go.work` at the repo root; it's optional and
never part of the contract.

Gate on what the contract tells you about the environment, never on which
harness is running. If a test needs to know the harness name, it's
category 3.

`APP_TEST_CLUSTER_TYPE` is about capability, not which harness. `kind`
usually being ATS and `capi` usually being atf is a coincidence, and gating
on it as a stand-in for the harness is wrong even when it happens to work.
Gate on what you actually need: if a test needs cloud identity, check for
that, so an `external` cluster with cloud identity passes the same gate. If
what you need isn't in any contract variable, the test needs harness
machinery, which is category 3.

### Conformance and ownership

Two runners, one contract, so they'll drift unless something checks. The
contract ships a conformance suite: a fixture `tests/app/` (trivial app, one
test per type, a hook, a lockfile) and assertions on the env vars, ordering,
exit codes, and lints above. A runner conforms only if it passes the suite
in CI; ATS and atf both wire it in. New guarantees go into the suite in the
same PR that adds them here.

Passing per runner isn't enough: both can pass and still disagree on what a
test sees, which is the drift that hurts (a smoke test that's green on PR
and flaky at night). So the suite also checks parity: the same fixture
through both runners has to collect the same counts and end with the same
result, or the suite fails. The known trap is guarantee 2, "settled": ATS
gets there when the Helm release reports installed, atf when the App CR
reads `deployed`, and those aren't the same moment. The contract pins the
observable, not the mechanism: settled means the app's own workloads are
Available, and the parity fixture checks that neither runner starts tests
early. `clustertest.wait.IsDeploymentReady` is the shared definition of
ready.

team-tenet owns the contract: this doc, the suite, and the call when the
runners disagree. team-honeybadger owns ATS, team-bumblebee owns atf.
Changing the contract is a PR here that updates the suite. A runner lagging
is a bug in that runner, not a reason to fork.

## Implementation

- **apptest-framework** gets a convention-runner: after the workload cluster
  and App CR are up, it grabs the WC kubeconfig
  (`Framework.GetClusterKubeConfig`), writes it out, exports the env
  contract, picks the executor, and runs it per type. For upgrades it adds
  the pre run. Today it runs the suite once after the upgrade; now it also
  runs `upgrade` tests against the old version first
  (`APP_TEST_UPGRADE_STAGE=pre`). `BeforeUpgrade` maps to the `pre-upgrade`
  hook. The image adds `uv` and `gotestsum`. In-process suites are
  untouched. Two things make this cheap: Ginkgo runs under plain `go test`,
  and pytest tests built on pytest-helm-charts already read `KUBECONFIG`, so
  existing ATS tests in either language run on workload clusters as-is.
- **app-test-suite** exports the `APP_TEST_*` names next to the old `ATS_*`
  ones (including `APP_TEST_UPGRADE_STAGE`, which it already has pre/post
  runs for), keeps its hook flags and also discovers the convention hooks by
  path (stopping if a flag and a file point at the same one), and adds a
  pre-deploy point for `setup`. Its `--app-tests-pre-hook` runs after
  deploy, so `setup` is a new call between `_ensure_cluster_prerequisites`
  and the install. It looks in `tests/app/` as well as today's `tests/ats/`,
  reads the shared config, and emits junit via gotestsum. Its upgrade
  pre/post behavior doesn't change. Its TEST_CONTRACT.md becomes a pointer
  here plus ATS-specific detail.
- **clustertest** gets `wait.IsDeploymentReady(name, namespace)` so both
  runners and the atf-native suites share one definition of ready, and the
  parity check has one thing to assert against.
- **the on-demand trigger**: the workload-cluster pipeline runs on `/run`
  against a PR, not just nightly, so a cloud-path change can get its result
  without waiting.
- **the conformance suite** lives here with the RFC: the fixture app and the
  assertions, parity check included. Both runners run it in CI; it's what
  "conforms" means.
- **devctl `gen apptest` and template-app** scaffold the layout for new
  repos.
- Migration happens as repos get touched; no flag day. Pilot:
  [giantswarm/muster#954](https://github.com/giantswarm/muster/pull/954).

## Alternatives considered

- **A shared assertions library both harnesses import per repo.** Tried it
  in muster; the module, replace directives, and adapter code guarded about
  a dozen lines of predicate per repo. Not worth it; better to align the
  runners so the test files themselves are shared.
- **Standardize on Ginkgo.** Ginkgo runs under `go test`, so it's allowed,
  but requiring it would shut out the pytest repos and tie the contract to a
  framework for nothing. We standardize selection and inputs, not the
  framework.
- **A `values: {ats: ..., e2e: ...}` map in the shared config.** No: it puts
  harness names in the neutral file, which is the config version of gating a
  test on the harness.
- **One runner with two modes instead of two behind a contract.** One runner
  covering kind and workload clusters wouldn't need a contract at all. But
  the two modes line up with two mature codebases owned by two teams
  (ATS/honeybadger, atf/tenet), each with provisioning and pipeline code the
  other doesn't want. Merging them is a bigger, riskier job than aligning
  their edges, and the parity check gets most of the anti-drift value for
  far less. Revisit if the runners keep drifting.
