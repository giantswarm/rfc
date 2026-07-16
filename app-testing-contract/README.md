---
creation_date: 2026-07-07
issues: []j
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

## Glossary

- test toolkit: the test runner and orchestrator, either `app-test-suite` (ATS) or `apptest-framework` (ATF)
- test framework: software framework used to implement the tests, e.g. Ginkgo or pytest
- test suite: a collection of tests, usually in one repo, that test a specific chart (app)

## Problem

We test our helm charts delivering managed apps using two toolkits: `app-test-suite` (ATS) and
`apptest-framework` (ATF). So far, it was not clear which toolkit teams should use and how to write the tests.
We propose to keep both toolkits, but specialize them to the two most frequent use cases:

- **app-test-suite (ATS)** - should provide rapid local feedback on PRs and in local dev environments. Its
  goal is to deploy the helm chart under tests as fast as possible and start testing the chart's
  functionality. This means that it will sacrifice all the possible real cluster features to achieve this
  goal. The cluster environment it is meant to run is `kind`, although it doesn't make any assumption about
  the cluster type.
- **apptest-framework (ATF)** takes the opposite approach: it chooses environment realism over the time needed
  to execute the tests. It creates a real workload cluster, installs the chart using the App Platform, and
  runs the full suite, preferably nightly.

With this in mind, it's clear that to provide a comprehensive test coverage and to follow the "fail fast"
principle, we need to use both toolkits.

The trouble is writing the tests (test suites). The tests author doesn't want to implement the same or very
similar set of tests twice, once for each toolkit. The goal of this doc is to propose a test implementation
spec that will allow both ATS and ATF to run the same test suites in their respective environments. Full
parity of tests might not be possible, as test itself might depend on the environment, but we want to get as
close as possible. A local kind cluster is fast but can't do cloud identity, real storage, or upgrades; a
workload cluster can. If a test suite needs to be aware of these differences, the author needs to get the
possibility to gate on the capabilities it needs.

This goal of this RFC is not to dedupe existing tests. It's to define how the two toolkits are different, what
environments they provide and what is the convention that, when respected, can allow to fit both toolkits with
the same test code.

## Decisions

### ATS and ATF

We keep both toolkits, but specialize them to the two most frequent use cases:

- `ats` is meant for rapid feedback testing on PRs and in local dev environments. It deploys the helm chart
  under tests as fast as possible and starts testing the chart's functionality. It sacrifices all the possible
  real cluster features to achieve this goal.
- `atf` takes the opposite approach: it chooses environment realism over the time needed to execute the tests.
  It creates a real workload cluster on a GS installation, installs the chart using the App Platform, and runs
  the full suite as a batch run, preferably nightly.
- we want a test development convention that will allow app maintainers to write tests once and run them under
  both toolkits, with the same test code.

### Test Development Convention

#### Assumptions

To avoid forcing a specific test framework or technology on test authors, we decided to make a convention that
tests are executed as a separate process by the test toolkits. The only requirements are that:

- for each test suite, we group all the tests into:
  - **smoke**: very basic tests that check if the app is deployed and running, and if the main functionality
    is working and worth even trying actual functional test. They should be fast, simple and reliable.
  - **functional**: tests that check the actual functionality of the app, and that it behaves as expected.
    They should be more complex and cover more scenarios than smoke tests.
  - **upgrade**: tests that check if the app can be upgraded from a previous version, by default the last
    stable version available in the OCI registry. The tests from this groups are executed twice, once before
    the upgrade (the "old" version, that we start the upgrade test with) and once after the upgrade (the "new"
    version, under the test).
- a single test can be of multiple types, for example a test that checks if the app is deployed and running
  can be both smoke and functional; a test that checks if the main page of an app loads can (and probably
  should) be functional and upgrade.
- tests need to be runnable with `go test` (golang) or `pytest` (python), and are using test filtering to run
  only the tests of a specific type (smoke, functional, upgrade). The test filtering is done with build tags
  (golang) or markers (python).
- all the information about the test environmenrt is passed to the tests via environment variables, and the
  tests should not depend on any other external information (like a config file or a specific cluster setup).
  The test toolkits are responsible for setting up the environment and passing the information to the tests.
- exit code `0` means the test run passed and at least 1 test was executed, exit code `5` means there was no
  error, but no test was executed at all, and any other non-zero exit code means the test run failed.
- test developer can deliver hooks that are executed by the test toolkits (see below).

#### The conventional directory

Tests live in one directory: `tests/app/`. Any harness that deploys the app runs that directory the same way.
An empty `tests/app/` (no module, no project) isn't an opt-in and is skipped.

It's either one Go module or one Python project, not both. The runner picks the executor from what's there:

- `go.mod`: `go test -mod=readonly -tags=<type>`
- `pyproject.toml`: `uv sync --frozen && uv run pytest -m <type>`
- both, or neither in a non-empty directory: config error, stop.

Dependencies are pinned from committed lockfiles (Go `go.sum`, Python `uv.lock`) and installed with
readonly/frozen flags.

#### Test types

Each test carries one type, set with a Go build tag or a pytest marker. There are three, the same ones ATS
already has:

| Type         | Runs                           | What it is                                   |
| ------------ | ------------------------------ | -------------------------------------------- |
| `smoke`      | normal flow, first             | quick sanity checks                          |
| `functional` | normal flow, after smoke       | full feature tests                           |
| `upgrade`    | upgrade flow, before and after | checks the app still works across an upgrade |

`upgrade` is its own type, not a flag on the others. The upgrade flow doesn't re-run smoke and functional; it
runs the `upgrade` tests, once for the "old" version (the version to test the upgrade from, usually the last
stable version) and once after upgrading to the "new" version (the version under test). The first run is the
baseline: if it passes and post fails, the upgrade caused it, and the upgrade test fails.

Most upgrade checks are symmetric ("the app answers") and assert the same thing both times. When some state
has to survive the upgrade, either seed it in the `pre-run` hook and check it in the post run, or keep it in
one test that branches on the stage:

```go
if os.Getenv("APP_TEST_UPGRADE_STAGE") != "post" {
    t.Skip("verification runs after the upgrade")
}
```

Seeding is a side effect, so it's a hook; checking is an assertion, so it's a test. Upgrade tests and hooks
hook also get `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION`.

#### Hooks

Hooks do things with side effects (install a prerequisite, create a pod, clean up); tests check things. Hooks
are delivered as executables in the `tests/app/hooks/` directory, and are optional. They should be implemented
in platform-independent way, preferably in bash or python. Hooks are executed by the test toolkit. Splitting
them is what lets the upgrade flow seed state without re-running a suite. Hooks get the test information
through environment variables, the same as tests. The hooks are:

| Hook                       | Runs                                                                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| `tests/app/hooks/setup`    | after the cluster is ready, before the app is deployed (for example: install prerequisites, CRDs)  |
| `tests/app/hooks/pre-run`  | Run before every test suite invocation, for each detected test types                               |
| `tests/app/hooks/post-run` | Run after every test suite invocation, for each detected test types                                |
| `tests/app/hooks/teardown` | after all tests, before the harness tears anything down (for example: clean up external resources) |

A missing hook is ignored. A non-zero exit fails the test run.

#### Full Test Flow

The test suite is always invoked by the test toolkit (`ats` or `atf`). The toolkit runs the tests using this
flow:

1. Test toolkit detects that tests are present in `tests/app/`.
1. Test toolkit installs software dependencies for the test suite (go or python) using the lockfile in
   `tests/app/`.
1. Test toolkit prepares the cluster used for testing (installs tools or dependencies it needs to execute
   tests; might be a no-op, depends on the test toolkit).
1. If present, the `setup` hook runs after the cluster is ready, before the app is deployed.
1. The app is deployed using the passed helm chart and the installation is settled (chart install exists
   cleanly).
1. For each test `type` in `smoke`, `functional`:
   1. `pre-run` hook runs for `type` tests (if present).
   1. Tests are executed for `type` type, using either `go test` or `pytest`, depending on the detected module
      type.
   1. `post-run` hook runs for `type` tests (if present).
1. If there are `upgrade` tests:
   1. If the version under test (new) is already installed in the cluster, it is uninstalled.
   1. The "old" stable version of the app is installed.
   1. `pre-run` hook runs for `upgrade` tests (if present).
   1. `upgrade` type tests are executed for the "old" version.
   1. `post-run` hook runs for `upgrade` tests (if present).
   1. The app is upgraded to the "new" version.
   1. `pre-run` hook runs for `upgrade` tests (if present).
   1. `upgrade` type tests are executed for the "new" version.
   1. `post-run` hook runs for `upgrade` tests (if present).
1. The app is uninstalled.
1. If present, the `teardown` hook runs after all tests, before the harness tears anything down.

#### Inputs

Tests get all the information about what is being tested from the environment variables. The following
variables are guaranteed to be set by the test toolkit before the tests are executed:

| Variable                                                        | Required          | Meaning                                                                                                                                                                                                                                       |
| --------------------------------------------------------------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `KUBECONFIG`                                                    | yes               | kubeconfig of the cluster the app is deployed on (never the MC)                                                                                                                                                                               |
| `APP_TEST_TYPE`                                                 | yes               | the type currently being run (`smoke`, `functional`, `upgrade`)                                                                                                                                                                               |
| `APP_TEST_TOOLKIT`                                              | yes               | The name of the toolkit running the tests (`ats` or `atf`)                                                                                                                                                                                    |
| `APP_TEST_RELEASE_NAME`                                         | yes               | Helm release name of the app under test                                                                                                                                                                                                       |
| `APP_TEST_RELEASE_NAMESPACE`                                    | yes               | namespace the app is deployed into                                                                                                                                                                                                            |
| `APP_TEST_CHART_VERSION`                                        | yes               | version of the chart under test                                                                                                                                                                                                               |
| `APP_TEST_CLUSTER_TYPE`                                         | yes               | type of the cluster the app runs on - a label: `kind` (local single-node), `capi` (a CAPI workload cluster), or `external` (a cluster the runner did not provision). Describes shape, not capability; gate on `APP_TEST_CAPABILITIES` instead |
| `APP_TEST_CAPABILITIES`                                         | yes               | comma-separated capabilities the cluster actually provides, e.g. `cloud-identity,persistent-storage,load-balancer`; empty is valid. The runner sets it from what it provisioned or was handed. This is what a test gates on                   |
| `APP_TEST_KUBERNETES_VERSION`                                   | optional          | Kubernetes server version                                                                                                                                                                                                                     |
| `APP_TEST_VALUES_FILE`                                          | optional          | values file the app was deployed with                                                                                                                                                                                                         |
| `APP_TEST_UPGRADE_STAGE`                                        | upgrade flow only | `pre` or `post`: which side of the upgrade this `upgrade`-type run is on                                                                                                                                                                      |
| `APP_TEST_UPGRADE_FROM_VERSION` / `APP_TEST_UPGRADE_TO_VERSION` | upgrade flow only | versions on either side of the upgrade                                                                                                                                                                                                        |

**Note**: These values come originally from `ats`, but are renamed here to match the test framework
independence. Four names are renamed, because the old ones were unclear or, for the upgrade stage, were never
test-facing under one name to begin with:

| Legacy                                                            | Canonical                     | Note                                                                                                                                                                 |
| ----------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ATS_TEST_TYPE`                                                   | `APP_TEST_TYPE`               | straight rename                                                                                                                                                      |
| `ATS_APP_CONFIG_FILE_PATH`                                        | `APP_TEST_VALUES_FILE`        | straight rename                                                                                                                                                      |
| `ATS_CLUSTER_VERSION`                                             | `APP_TEST_KUBERNETES_VERSION` | straight rename                                                                                                                                                      |
| `ATS_EXTRA_UPGRADE_TEST_STAGE` (tests) / `ATS_HOOK_STAGE` (hooks) | `APP_TEST_UPGRADE_STAGE`      | value also changes: `pre_upgrade`/`post_upgrade` become `pre`/`post`. The runner does not alias the value, so existing upgrade tests reading the old one must update |

`ATS_CHART_PATH` and `ATS_TEST_DIR` have no `APP_TEST_` equivalent; the contract doesn't expose them and they
stay ATS-only. `APP_TEST_CAPABILITIES` is new, computed by the runner, with no `ATS_` predecessor.
`KUBECONFIG` stays as-is; it's the standard name, not ours.

#### Capabilities

The cluster intended for PR testing is `kind`. As a simple cluster instance, it lacks features like cloud
identity, real storage, or load balancers. Tests that need those capabilities should gate on the
`APP_TEST_CAPABILITIES` and only run nightly on a real workload cluster.

We define the following capabilities, which the toolkit sets in `APP_TEST_CAPABILITIES`:

- cloud-identity
- persistent-storage
- load-balancer

# TODO: define and complete the capabilites list

### Toolkit outputs

Toolkits should let the test frameworks they execute to log to stdout/stderr, and should not filter or
redirect the output. Test toolkit exit code `0` means the test run passed and at least 1 test was executed,
exit code `5` means there was no error, but no test was executed at all, and any other non-zero exit code
means the test run failed.

### Shared toolkit configuration

Test toolkits need to know some information about how to handle the helm chart under test, i.e. in which
namespace it should be installed or what `values.yaml` file should be used. This information has to be easily
set in CI/CD pipelines, where config files are not convenient when the configuration has to be dynamic. Thus,
we propose a shared optional config file that both toolkits should use. Each of the config options in the file
must accept environment variable overrides, as specified below. Each test toolkit should print the effective
configuration it is using at the start of the toolkit run.

Test _code_ lives in `tests/app/`; shared _configuration_ lives in `.apptest/`. `.apptest/config.yaml` holds
only what both toolkits need, and the chart values files. The config schema is (with default values and
respective env vars):

```yaml
releaseNamespace: default # APP_TEST_RELEASE_NAMESPACE
testTypes: [smoke, functional, upgrade] # APP_TEST_TEST_TYPES="a,b,c" - normally autodetected
chartConfig:
  shared: # optional configuration files, applied and merged in the list order, shared between both toolkits
    valueFiles:
      - file1.yaml
      - file2.yaml
  toolkitSpecific: # mutually exclusive with chartConfig.shared
    - name: ats # ATS reads its own entry
      valueFiles:
        - file1.yaml
        - file2.yaml
    - name: atf # apptest-framework reads its own entry
      valueFiles:
        - file1.yaml
        - file2.yaml
```

# TODO: just a config proopsal, discuss

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
