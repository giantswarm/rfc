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

We run "does the deployed app actually work" checks at two cadences, on
purpose:

- **app-test-suite (ATS)** deploys the chart on a kind cluster and runs
  fast checks per pull request.
- **apptest-framework (atf)** stands up a workload cluster on a management
  cluster, installs an App CR, and runs the full suite nightly.

Both cadences earn their keep and we are keeping both: kind gives quick
per-PR signal, a real workload cluster catches what kind cannot (cloud
identity, real storage, upgrades). The split is not the problem. The
problem is that the two harnesses have divergent authoring models: ATS
expects pytest or plain Go, atf expects Ginkgo suites. Covering both
cadences means writing the same check twice in two idioms, so in practice
a repo writes it for one harness, or for neither. Adoption of both is
close to zero, and teams that did adopt a single harness are often
unhappy living in two worlds.

So this RFC is not a dedup exercise; there is little duplication to
remove, because the double-idiom cost suppressed writing the tests in the
first place. It unifies the *authoring* model: one directory, one idiom
per repo, discovered and run the same way by both harnesses. A test
written once runs per-PR on kind (the subset kind can support) and nightly
on a workload cluster (everything), with no second copy to keep in sync.

ATS already publishes a testing contract
([docs/TEST_CONTRACT.md](https://github.com/giantswarm/app-test-suite/blob/master/docs/TEST_CONTRACT.md)),
but it lives in one harness's repo and only that harness implements it.
This RFC extracts the contract, makes it harness-neutral, and extends
apptest-framework to implement it too. The contract is deliberately not
tied to a test framework or language.

## Decision

### The conventional directory

Each app repo has one conventional test directory: `tests/app/`. It
contains the app's tests, written against the contract below. Any harness
that deploys the app runs this directory the same way. Presence of the
directory is the opt-in; there is no per-repo wiring.

The directory is one Go module or one Python project, never both. The
executor is detected from its contents:

- `go.mod` present: `go test -mod=readonly -tags=<type>`
- `pyproject.toml` present: `uv sync --frozen && uv run pytest -m <type>`
- both present, or neither present in a non-empty directory:
  configuration error, fail fast

Dependencies are pinned and installed offline: Go reads a committed
`go.sum` under `-mod=readonly`, Python a committed `uv.lock` under
`--frozen`. A runner never resolves versions from the network at test
time; a missing or stale lockfile is a failure, not a silent fetch. This
keeps the dependency closure identical across harnesses and auditable.

An empty `tests/app/` (no module, no project) is not an opt-in and is
ignored.

### Test types

A test declares its type via a Go build tag or pytest marker. There are
three peer types, matching ATS's existing `StepType`s; a test carries one.

| Type | Runs | Meaning |
|---|---|---|
| `smoke` | normal flow, first | fast, fail-fast sanity checks |
| `functional` | normal flow, after smoke | full feature tests |
| `upgrade` | upgrade flow, before and after the upgrade | verifies the app still works across an upgrade; the pre run is the baseline |

`upgrade` is a peer type, not a modifier on the others. The upgrade flow
does not re-run the `smoke` and `functional` suites; it runs only the
`upgrade`-typed tests. It runs them twice: once on the old version before
the upgrade (`APP_TEST_UPGRADE_STAGE=pre`) and once after
(`APP_TEST_UPGRADE_STAGE=post`). The pre run is the baseline that makes a
post failure attributable to the upgrade rather than to a pre-existing
break. This is ATS's existing behavior; atf gains the pre run.

A symmetric invariant ("the app answers") is just an `upgrade` test that
asserts the same thing on both sides, and gets the baseline for free. The
asymmetric case (state that must survive the upgrade) has two shapes. When
the "before" step is a pure side effect, seed it in the `pre-upgrade` hook
and verify in the `post` run. When it is easier to keep in one file, a
single test branches on the stage:

```go
if os.Getenv("APP_TEST_UPGRADE_STAGE") != "post" {
    t.Skip("verification runs after the upgrade")
}
```

Seeding-as-side-effect belongs in a hook, not a test that reruns;
verification is an assertion, so it is a test. Upgrade tests and the
`pre-upgrade` hook also receive `APP_TEST_UPGRADE_FROM_VERSION` /
`APP_TEST_UPGRADE_TO_VERSION`.

Assertions live in tests; setup, teardown, and upgrade seeding live in
hooks (next section).

### Hooks

Hooks do imperative work with a side effect (install a prerequisite, seed
a pod, clean up an external resource); tests assert. Keeping the two
separate is what lets the upgrade flow seed state without re-running a test
suite. Setup, seeding, and teardown are app-specific just like assertions
and duplicate across harnesses the same way, so the contract defines
portable hooks: optional executables in the conventional directory, invoked
by the runner with the same environment as tests.

| Hook | Runs |
|---|---|
| `tests/app/hooks/setup` | after the cluster is ready, before the app is deployed (for example: install prerequisites) |
| `tests/app/hooks/pre-upgrade` | upgrade flow only: after the previous version is deployed, before the upgrade (for example: create a pod or write a record whose survival an `upgrade` test then verifies) |
| `tests/app/hooks/teardown` | after all tests, before the harness tears anything down (for example: clean up external resources) |

A hook is any executable file at that path: a script with a shebang or a
built binary, invoked directly (not sourced, not run through a language
toolchain). Because it runs out of process, it is exempt from the
directory's one-language rule and may be written in whatever suits it;
keep it thin, since anything substantial belongs in a test or a
harness-native hook.

A missing hook is a no-op. A non-zero exit fails the run. Hooks gate on
environment properties exactly like category-2 tests (`APP_TEST_CLUSTER_TYPE`
and friends); the `pre-upgrade` hook additionally receives
`APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION`.

Convention discovery of these three paths is the portable, zero-wiring
default a conforming runner must implement. A harness may *also* keep its
own config-wired hook flags, so existing repos need no immediate move and
harness-specific points stay available. Where a flag targets one of the
three contract points, it and the convention hook are alternatives: if both
are set for the same point, the runner fails fast (as with a directory that
has both `go.mod` and `pyproject.toml`), so migration is "drop the file,
remove the flag" in one change rather than a silent double-run. Only the
convention path is a contract guarantee and exercised by the conformance
suite; the flags are harness-native.

How each harness supplies the three contract points today:

| Contract hook | ATS | atf |
|---|---|---|
| `setup` (before deploy) | new pre-deploy point (its `--app-tests-pre-hook` fires after deploy) | `AfterClusterReady` (runs before install) |
| `pre-upgrade` | `--upgrade-tests-upgrade-hook` at `PRE_UPGRADE` | `BeforeUpgrade` |
| `teardown` (after tests) | `--app-tests-post-hook` | suite callback |

Each runner satisfies a point either by discovering the convention file or
through the mapped flag, not both at once. Points outside this table
(ATS's `POST_UPGRADE` stage, its pre/post test hooks) stay harness-native.

The boundary is the same as for tests: a portable hook only gets the app
cluster's `KUBECONFIG`. Work that needs the harness's own machinery (MC
access, App CR manipulation, framework state) stays in harness-native
hooks: ATS's config-wired hooks at points the contract does not cover (its
pre/post *test* hooks, the `post-upgrade` stage) and atf's suite callbacks
(`AfterClusterReady`, `BeforeUpgrade`), which remain available and are not
part of this contract.

### Inputs

Tests receive everything through the environment. They never provision:
no cluster creation, no chart install, no App CRs.

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

The canonical prefix is `APP_TEST_`, neutral to both harnesses. The
existing implementation publishes these variables under the legacy `ATS_`
prefix; conforming runners export both, so no existing test breaks and
dual export costs nothing ongoing. New and scaffolded tests use
`APP_TEST_`. The mapping is mechanical (`ATS_X` becomes `APP_TEST_X`)
with three exceptions renamed for clarity:

| Legacy | Canonical |
|---|---|
| `ATS_TEST_TYPE` | `APP_TEST_TYPE` |
| `ATS_APP_CONFIG_FILE_PATH` | `APP_TEST_VALUES_FILE` |
| `ATS_CLUSTER_VERSION` | `APP_TEST_KUBERNETES_VERSION` |

`KUBECONFIG` is unchanged: it is the Kubernetes-wide convention, not ours.

### Runner guarantees

A conforming runner guarantees, before invoking the executor:

1. the `setup` hook, if present, ran after the cluster was ready and
   before the app was deployed,
2. the app is deployed and settled (ATS: chart installed via Helm or a
   GitOps engine; atf: App CR reconciled to `deployed`),
3. all required variables above are exported,
4. the `teardown` hook, if present, runs after the last test type, before
   the harness's own teardown.

In the **normal flow**, the executor is invoked once per applicable test
type, in order: `smoke`, then `functional`. `upgrade`-typed tests do not
run here.

In the **upgrade flow** (`upgrade: true`), the runner: deploys the previous
version and waits for it to settle, invokes the executor for the `upgrade`
type with `APP_TEST_UPGRADE_STAGE=pre` (the baseline), runs the
`pre-upgrade` hook if present, upgrades to the version under test and waits
for it to settle, then invokes the executor for the `upgrade` type with
`APP_TEST_UPGRADE_STAGE=post`. The `smoke` and `functional` suites are not
part of this flow.

"No tests for this type" is a pass, not a failure (Go: build constraints
exclude all files; pytest: exit code 5), because a repo may legitimately
carry only some types. Zero collection is never silent, though: the runner
records the collected count per type, so a typo'd tag or marker (which also
collects zero) is visible in the output rather than a green run. Repos that
want it enforced list the types they expect in `config.yaml` (see below);
a listed type collecting zero fails the run. Test results are emitted as
junit XML: `gotestsum --junitfile` for Go, `pytest --junitxml` for Python.

### Cadence and feedback latency

The two cadences buy quick per-PR signal at the cost of a gap: the fast
runner on kind cannot exercise what kind lacks (cloud identity, real
storage, load balancers), so a test gated to those environments runs only
in the nightly workload-cluster flow. Its signal is then detached from the
change that broke it. A pull request that breaks a cloud-only path passes
per-PR CI green and fails nightly, hours later, against a batch of
unrelated commits.

This is an accepted property of the split, not a defect the contract
introduces, but the contract must not let it be silent or unescapable:

1. **A nightly-only test is a conscious choice, never an accident.** A
   test that gates itself off kind (category 2) is by construction
   per-PR-invisible. Reviewers see that in the diff; the collected-count
   output makes "ran nowhere per-PR" legible rather than looking like
   coverage.
2. **There is an on-demand full-flow trigger.** A change that touches a
   cloud-only path can request the workload-cluster flow against the pull
   request instead of waiting for the scheduled run, via the existing
   `/run` pipeline convention. Catching a cloud regression a day late is
   the default; paying for it on the PR is one comment away.

Prefer expressing a real capability need over a hard environment gate (see
`APP_TEST_CLUSTER_TYPE` below): a test that only needs cloud identity, not
kind-vs-WC specifically, will also run per-PR on any `external` cluster
that provides it, which shrinks the nightly-only set.

### Shared configuration

`tests/app/config.yaml` carries only the keys both harnesses need:

```yaml
contractVersion: 1            # contract version this directory targets
installNamespace: kube-system
upgrade: true                 # whether an upgrade flow applies to this app
expectedTypes: [smoke, functional, upgrade]   # optional: types that must collect at least one test
```

`upgrade` is the declarative form of each harness's existing upgrade
primitive: atf's `WithIsUpgrade(true)` (install the latest release,
upgrade to the version under test) and ATS's upgrade scenario. It is
explicit rather than inferred from the presence of `upgrade`-typed tests
because the upgrade flow is the expensive one.

The two settings lint against each other and against what is collected, so
a mistake fails the run instead of passing green:

- `upgrade: true` with zero `upgrade`-typed tests collected fails (dead
  flow, or a typo'd tag).
- `upgrade`-typed tests present with `upgrade` unset or false fails (tests
  that would never run).
- any type in `expectedTypes` collecting zero fails; `expectedTypes` is
  optional, and omitting it keeps the permissive "no tests is a pass"
  default for repos that do not want the check.

Everything harness-specific stays in the harness's own config:
`.ats/main.yaml` (cluster types, catalogs, executor options) and
`tests/e2e/config.yaml` (appCatalog, providers, MC test options). Values
files also stay per harness: values legitimately differ between a kind
cluster and a workload cluster, and each provisioner consumes them through
its own mechanism.

### Harness-specific tests

The contract covers the default case, not everything. Where a test goes:

1. Asserts on the deployed app and works on any cluster: `tests/app/`,
   no gate. This should be the bulk.
2. Asserts on the deployed app but is only meaningful in one environment:
   `tests/app/` plus a runtime skip on contract environment, for example
   `if os.Getenv("APP_TEST_CLUSTER_TYPE") != "kind" { t.Skip(...) }`. Skips
   stay visible by name in both runners' output.
3. Needs harness machinery (MC access, bundle installs, AWS/IRSA, cluster
   manipulation): a regular in-process apptest-framework suite under
   `tests/e2e/suites/`, unchanged by this RFC.

A repo may therefore hold two Go modules, `tests/app/` (portable) and
`tests/e2e/` (atf-native), each with its own `go.mod`. They stay separate
modules on purpose: the portable one must build without the atf
dependency tree. Repos that want unified tooling across them add a
`go.work` at the repo root; it is not required and is never committed as a
contract artifact.

Tests may gate on environment properties the contract exposes, never on
which harness is running them. A test that needs the harness's name
belongs in category 3.

`APP_TEST_CLUSTER_TYPE` is a capability axis, not a harness label. That
`kind` tends to mean ATS and `capi` tends to mean atf today is
incidental, and a gate written as "am I really asking about the harness?"
is a category error even when it happens to work. Gate on the property you
actually depend on: if a test needs cloud identity, express that (and let
`external` clusters that also provide it pass the same gate) rather than
hard-coding `!= "kind"`. If the property you need is not on any contract
variable, the test needs harness machinery and belongs in category 3.

### Conformance, versioning, and ownership

Two independent runners implement one contract, so drift is the default
failure mode unless something mechanically checks them. The contract ships
with a conformance suite: a fixture `tests/app/` (a trivial app, one test
of each type, one hook, a lockfile) plus a set of assertions on the
env-var, ordering, exit-code, and lint guarantees above. A runner is
conforming only if it passes the suite in its CI; both ATS and atf wire it
in. New guarantees land in the suite in the same change that adds them
here.

Per-runner conformance is necessary but not sufficient: two runners can
each satisfy the letter of the contract and still disagree on what a test
observes, which is the failure that actually bites (a smoke test that
passes fast-CI and flakes nightly). The suite therefore also asserts
*parity*: the same fixture run through both runners must yield the same
collected-per-type counts and the same pass/fail outcome, and any
divergence fails the suite. The known sharp edge is guarantee 2, "the app
is settled": ATS reaches it via a Helm release reporting installed, atf
via an App CR reconciled to `deployed`, and those are not the same instant.
The contract fixes the observable, not the mechanism: settled means the
app's own readiness (its Deployments/StatefulSets Available) holds, and the
parity fixture asserts a runner does not hand off to tests before it does.
`clustertest.wait.IsDeploymentReady` is the shared vocabulary for that
check so both runners and the tests mean the same thing by "ready".

The contract is versioned. This document is `v1`; the version is declared
in `tests/app/config.yaml` as `contractVersion: 1`. A runner refuses a
directory whose declared version it does not implement rather than
guessing. Breaking changes bump the integer and the conformance suite
carries a fixture per supported version.

team-tenet stewards the contract (owns this document and the conformance
suite, arbitrates when the two runners disagree). team-honeybadger and
team-bumblebee own the ATS and atf implementations respectively. A change
to the contract is a PR here that updates the suite; a runner falling
behind is a bug against that runner, not a licence to fork the contract.

## Implementation

- **apptest-framework** gains a convention-runner: after provisioning the
  workload cluster and App CR, it fetches the WC kubeconfig
  (`Framework.GetClusterKubeConfig`), writes it to a file, exports the env
  contract, detects the executor, and runs it per test type. For the
  upgrade flow it gains the pre run: it runs the `upgrade` type against the
  previous version (`APP_TEST_UPGRADE_STAGE=pre`) before upgrading, where
  today it runs the suite once after. Its `BeforeUpgrade` callback maps onto
  the conventional `pre-upgrade` hook. The image gains `uv` and `gotestsum`.
  Existing in-process suites are unaffected. Enabling facts: Ginkgo runs
  under plain `go test`, and pytest tests built on pytest-helm-charts
  already read `KUBECONFIG`, so existing ATS tests of both languages are
  immediately reusable on workload clusters.
- **app-test-suite** exports the canonical `APP_TEST_*` names alongside its
  legacy `ATS_*` ones (including `APP_TEST_UPGRADE_STAGE` for the pre/post
  runs it already performs), keeps its existing hook flags and additionally
  discovers the conventional hooks by path (failing fast if a flag and a
  convention hook target the same point), and gains a pre-deploy hook point
  for `setup`: its `--app-tests-pre-hook` fires after deploy, so `setup`
  (before deploy, for prerequisites) is a new call between
  `_ensure_cluster_prerequisites` and the chart install. It searches
  `tests/app/` in addition to its current `tests/ats/` default, reads the
  shared config keys, and emits junit via gotestsum. Its upgrade pre/post
  behavior is unchanged. Its TEST_CONTRACT.md becomes a pointer to this RFC
  plus ATS-specific detail.
- **clustertest** gains `wait.IsDeploymentReady(name, namespace)` so both
  runners and non-portable suites share the same readiness vocabulary, and
  the settled-parity assertion has one definition to check against.
- **the on-demand full-flow trigger**: the workload-cluster pipeline runs
  on the `/run` convention against a pull request, not only on the nightly
  schedule, so a change touching a cloud-only path can pull its signal
  forward without waiting for the batch.
- **the conformance suite** lives in this repo alongside the RFC: the
  fixture app plus the guarantee assertions, including the cross-runner
  parity check. Both runners run it in CI; it is the acceptance gate for
  "implements the contract."
- **devctl `gen apptest` and template-app** scaffold the conventional
  layout for new repos.
- Migration is opt-in as repos get touched; there is no flag day.
  Pilot: [giantswarm/muster#954](https://github.com/giantswarm/muster/pull/954).

## Alternatives considered

- **A shared assertions library consumed by both harnesses per repo.**
  Prototyped in muster; the module, replace directives, and adapter
  helpers protected a dozen lines of predicate logic per repo. Rejected in
  favor of aligning the runners so the test files themselves are shared.
- **Standardizing on Ginkgo as the contract.** Ginkgo runs under
  `go test`, so it is allowed, but mandating it would exclude the pytest
  repos and couple the contract to a framework for no gain. The contract
  standardizes selection and inputs, not the test framework.
- **A `values: {ats: ..., e2e: ...}` map in the shared config.** Rejected:
  it bakes harness names into the neutral file, the configuration
  equivalent of a test gating on the harness's name.
- **One runner with two modes instead of two runners behind a contract.**
  A single runner covering both fast-kind and workload-cluster modes would
  need no contract to police, since there would be nothing to keep in step.
  Rejected because the two cadences map onto two mature codebases owned by
  two teams (ATS by team-honeybadger, atf by team-tenet), each carrying
  provisioning and pipeline machinery the other does not want. Collapsing
  them is a larger, riskier rewrite than aligning their edges, and the
  parity check gives most of the anti-drift benefit at a fraction of the
  cost. If the two runners keep diverging in practice, revisit this.
