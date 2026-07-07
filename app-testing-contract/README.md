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

We test managed apps with two harnesses. app-test-suite (ATS) deploys the
chart on a kind cluster in the PR pipeline. apptest-framework (atf) stands
up a workload cluster on a management cluster and installs an App CR in the
e2e pipeline. Both need "does the deployed app actually work" checks, and
today each repo writes them twice, in two idioms (pytest or plain Go for
ATS, Ginkgo suites for atf). In practice one side is usually empty or
stale.

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

- `go.mod` present: `go test -tags=<type>`
- `pyproject.toml` present: `uv sync && uv run pytest -m <type>`
- both present: configuration error, fail fast

### Test types

A test declares its types via Go build tags or pytest markers. A test may
carry several types.

| Type | Meaning |
|---|---|
| `smoke` | fast, fail-fast sanity checks, run first |
| `functional` | full feature tests |
| `upgrade` | runs twice during an upgrade flow: before and after the upgrade |

Types answer "what kind of test"; lifecycle position is not a type. The
upgrade flow runs `upgrade`-typed tests twice and tells them where they
are via `APP_TEST_UPGRADE_STAGE` (`pre` or `post`). The canonical asymmetric
upgrade test (seed a workload before, verify it survived after) branches
or skips on the stage:

```go
if os.Getenv("APP_TEST_UPGRADE_STAGE") != "post" {
    t.Skip("verification runs after the upgrade")
}
```

This keeps the type set identical to ATS's published contract (no
migration for existing tests) and matches the principle used everywhere
else in this contract: tests gate on environment properties. Pre-only
tests appear as named skips in the post run and vice versa, which is
accepted for the simpler taxonomy.

Assertions live in tests; setup and teardown live in hooks (next
section).

### Hooks

Setup and teardown are app-specific just like assertions, and duplicate
across harnesses the same way. The contract therefore defines portable
hooks: optional executables in the conventional directory, invoked by the
runner with the same environment as tests, plus `APP_TEST_HOOK_STAGE` naming
the point.

| Hook | Runs |
|---|---|
| `tests/app/hooks/setup` | after the cluster is ready, before the app is deployed (for example: install prerequisites) |
| `tests/app/hooks/teardown` | after all tests, before the harness tears anything down (for example: clean up external resources) |

A missing hook is a no-op. A non-zero exit fails the run. Hooks gate on
environment properties exactly like category-2 tests (`APP_TEST_CLUSTER_TYPE`
and friends); during upgrade flows they additionally receive
`APP_TEST_UPGRADE_STAGE` and the from/to versions.

The boundary is the same as for tests: a portable hook only gets the app
cluster's `KUBECONFIG`. Work that needs the harness's own machinery (MC
access, App CR manipulation, framework state) stays in harness-native
hooks: ATS's config-wired hook executables and atf's suite callbacks
(`AfterClusterReady`, `BeforeUpgrade`), which remain available and are
not part of this contract.

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
| `APP_TEST_CLUSTER_TYPE` | yes | `kind`, `external`, or `capi` |
| `APP_TEST_KUBERNETES_VERSION` | optional | Kubernetes server version |
| `APP_TEST_VALUES_FILE` | optional | values file the app was deployed with |
| `APP_TEST_UPGRADE_STAGE` | upgrade runs only | `pre` or `post`: which side of the upgrade this run is on |
| `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION` | upgrade runs only | versions on either side of the upgrade |
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

Before invoking the executor, a conforming runner guarantees:

1. the `setup` hook, if present, ran after the cluster was ready and
   before the app was deployed,
2. the app is deployed and settled (ATS: chart installed via Helm or a
   GitOps engine; atf: App CR reconciled to `deployed`),
3. all required variables above are exported,
4. the executor is invoked once per applicable test type, in order:
   `smoke`, then `functional`; for upgrade flows: `upgrade` with
   `APP_TEST_UPGRADE_STAGE=pre`, then the upgrade is performed, then `upgrade`
   with `APP_TEST_UPGRADE_STAGE=post`,
5. the `teardown` hook, if present, runs after the last test type, before
   the harness's own teardown.

"No tests for this type" is a pass, not a failure (Go: build constraints
exclude all files; pytest: exit code 5). Test results are emitted as junit
XML: `gotestsum --junitfile` for Go, `pytest --junitxml` for Python.

### Shared configuration

`tests/app/config.yaml` carries only the keys both harnesses need:

```yaml
installNamespace: kube-system
upgrade: true   # whether an upgrade flow applies to this app
```

`upgrade` is the declarative form of each harness's existing upgrade
primitive: atf's `WithIsUpgrade(true)` (install the latest release,
upgrade to the version under test) and ATS's upgrade scenario. It is
explicit rather than inferred from the presence of `upgrade`-typed tests
because the upgrade flow is the expensive one, and the combination is a
lint: `upgrade: true` with zero `upgrade`-typed tests collected fails the
run, catching typo'd tags and markers instead of silently passing.

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

Tests may gate on environment properties the contract exposes, never on
which harness is running them. A test that needs the harness's name
belongs in category 3.

## Implementation

- **apptest-framework** gains a convention-runner: after provisioning the
  workload cluster and App CR, it fetches the WC kubeconfig
  (`Framework.GetClusterKubeConfig`), writes it to a file, exports the env
  contract, detects the executor, and runs it per test type. The image
  gains `uv` and `gotestsum`. Existing in-process suites are unaffected.
  Enabling facts: Ginkgo runs under plain `go test`, and pytest tests
  built on pytest-helm-charts already read `KUBECONFIG`, so existing ATS
  tests of both languages are immediately reusable on workload clusters.
- **app-test-suite** exports the canonical `APP_TEST_*` names alongside
  its legacy `ATS_*` ones, adds the upgrade stage variable for test
  processes (hooks already get the equivalent), discovers
  the conventional hooks by path in addition to its config-wired ones,
  searches `tests/app/` in addition to its current `tests/ats/` default,
  reads the shared config keys, and emits junit via gotestsum. Its
  TEST_CONTRACT.md becomes a pointer to this RFC plus ATS-specific detail.
- **clustertest** gains `wait.IsDeploymentReady(name, namespace)` so
  non-portable suites share the same readiness vocabulary.
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
