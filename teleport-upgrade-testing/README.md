---
creation_date: 2026-01-21
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-shield
state: review
summary: Establish an automated testing pipeline to validate Teleport cluster version upgrades before applying to production. Deploy an ephemeral Teleport cluster with the current production version, connect ephemeral MCs, validate connectivity, upgrade to the target version, and re-validate.
---

# Teleport Cluster Version Upgrade Testing Pipeline

## Problem statement

Giant Swarm operates two Teleport clusters (`prod` and `test`) that provide secure access to all Management Clusters. Upgrading Teleport versions is currently a high-risk operation because:

1. **No pre-production validation**: We cannot test upgrades against real MC connectivity patterns before applying to production
2. **Version compatibility unknowns**: The compatibility between Teleport server, tbot, and teleport-kube-agent versions is not systematically validated
3. **Rollback complexity**: A failed upgrade in production affects all MC access, and rollback may not restore all connection state
4. **Manual process**: Upgrades require manual coordination and testing, leading to delayed version adoption

### Current state

**Teleport infrastructure components:**

| Component | Location | Purpose |
|-----------|----------|---------|
| Teleport Cluster | teleport-fleet | Central Teleport server (prod & test instances) |
| teleport-tbot | teleport-fleet | Bot authentication for CI/monitoring |
| teleport-operator | teleport-operator | Runs on MCs, manages Teleport integration |
| teleport-kube-agent (MC) | teleport-kube-agent | Registers Teleport clusters & apps |

> **Note:** The upgrade testing pipeline will deploy the **current production version** first, then upgrade to a **target version** to validate the upgrade path.

**Note:** The `teleport-operator` is a key component that runs on Management Clusters. It:
- Watches for Cluster CRs and registers them with Teleport
- Deploys `teleport-kube-agent` to clusters
- Uses its own tbot for authenticating to Teleport
- Configured via `teleport.proxyAddr` to point to the Teleport cluster

The existing `test` Teleport cluster cannot be used for upgrade testing because:

- It serves real ephemeral MCs during CI runs
- Upgrading it would disrupt ongoing CI pipelines
- It needs to remain stable as a baseline

### Impact of not solving

- Delayed adoption of Teleport security patches and features
- Risk of production incidents during upgrades
- Reduced confidence in upgrade process leading to version drift
- Potential compliance issues from running outdated versions

## Decision maker

Team Shield

## Deadline

Q2 2026

## Who is affected / stakeholders

- **Team Shield**: Owns Teleport infrastructure, teleport-operator, teleport-kube-agent
- **Team Tenet**: Owns Tekton CI pipelines
- **All teams using Teleport**

## Repositories involved

- [giantswarm/teleport-fleet](https://github.com/giantswarm/teleport-fleet) - Teleport cluster infrastructure (Terraform, Helm)
- [giantswarm/teleport-operator](https://github.com/giantswarm/teleport-operator) - Kubernetes operator for MC Teleport integration
- [giantswarm/mc-bootstrap](https://github.com/giantswarm/mc-bootstrap) - MC creation and Teleport integration
- [giantswarm/tekton-resources](https://github.com/giantswarm/tekton-resources) - CI pipeline definitions
- [giantswarm/workload-clusters-fleet](https://github.com/giantswarm/workload-clusters-fleet) - Workload clusters repo

## Preferred solution

Create an ephemeral Teleport cluster (`ci.teleport.giantswarm.io`) specifically for upgrade testing, integrated with mc-bootstrap and Tekton pipelines.

**Terminology:**
- **Current version**: The Teleport version currently running in production
- **Target version**: The new Teleport version we want to upgrade to and validate

### Architecture overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              gazelle-cicdprod                              │
│                                 (Tekton)                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Deploy     │───►│   Create     │───►│   Upgrade    │───►│  Cleanup  │ │
│  │   Teleport   │    │   MC &       │    │   Teleport   │    │           │ │
│  │   (current)  │    │   Validate   │    │   & Validate │    │           │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Ephemeral MC (*goshawk/gmc/goose/goten*-ci)      │   │
│  │                                                                     │   │
│  │  • teleport-kube-agent connects to ci.teleport.giantswarm.io        │   │
│  │  • Validates: tsh login, kube access, bot tokens                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AWS (Ephemeral Teleport - ci)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │    EKS      │    │  DynamoDB   │    │     S3      │    │  Route53    │  │
│   │ teleport-ci │    │  ci-state   │    │ ci-sessions │    │ ci.teleport │  │
│   │             │    │  ci-events  │    │             │    │ .giantswarm │  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component design

#### 1. Ephemeral Teleport cluster (ci)

A new Terraform environment in `teleport-fleet` that mirrors `test` but with:

- **Isolated state**: Separate S3 keys and DynamoDB tables
- **Cost optimization**: Smaller instance types (`t3.medium`), single replica
- **Parameterized version**: Teleport chart version passed as variable
- **DNS**: `ci.teleport.giantswarm.io`

```hcl
# terraform/envs/ci_infra/main.tf
locals {
  teleport_cluster_name = "ci"
}

module "infra" {
  source = "../../modules/infra"

  teleport_cluster_name  = local.teleport_cluster_name
  teleport_chart_version = var.teleport_chart_version  # Parameterized
  instance_type          = "t3.medium"                 # Cost optimized
  # ... other variables
}
```

#### 2. MC Bootstrap integration

A dedicated environment configuration pointing to the CI Teleport:

```bash
# mc-bootstrap/ci/*goshawk/gmc/goose/goten*-teleport-ci/env
export CONFIG_BRANCH=main
export MCB_BRANCH=main
export CMC_BRANCH=main
export MC_APP_COLLECTION_BRANCH=main
export INSTALLATIONS_BRANCH=master
export TELEPORT_CLUSTER=ci.teleport.giantswarm.io
```

#### 3. Connectivity validation

A validation script that tests all access patterns. In CI, we use a tbot-generated identity file (stored in a Kubernetes secret) for non-interactive authentication, similar to how `apply-teleport-bot.sh` works today.

```bash
#!/bin/bash
# mc-bootstrap/scripts/validate-teleport-connectivity.sh

set -euo pipefail

base_dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )
source "${base_dir}/scripts/utils.sh"

TELEPORT_CLUSTER="${TELEPORT_CLUSTER:-ci.teleport.giantswarm.io}"
INSTALLATION="${INSTALLATION:-*goshawk/gmc/goose/goten*}"
# The identity secret name depends on which Teleport cluster we're testing against
# For CI Teleport, we need a dedicated tbot identity secret
IDENTITY_SECRET="${TELEPORT_IDENTITY_SECRET:-ci-teleport-identity-output}"
IDENTITY_NAMESPACE="${TELEPORT_IDENTITY_NAMESPACE:-tekton-pipelines}"

echo "=== Teleport Connectivity Validation ==="
echo "Teleport Cluster: ${TELEPORT_CLUSTER}"
echo "Installation: ${INSTALLATION}"

# Get tbot-generated identity from secret
echo "---> Retrieving tbot identity from secret ${IDENTITY_SECRET}"
IDENTITY_FILE=$(mk_temp_file "teleport-identity")
kubectl get secret "${IDENTITY_SECRET}" -n "${IDENTITY_NAMESPACE}" \
  -o jsonpath='{.data.identity}' | base64 -d > "${IDENTITY_FILE}"

cleanup() {
  rm -f "${IDENTITY_FILE}"
}
trap cleanup EXIT

# Test 1: Proxy connectivity using identity file
echo "[1/4] Testing tsh login with identity file..."
"${TOOLS_FOLDER}/tsh" login --proxy="${TELEPORT_CLUSTER}:443" --identity="${IDENTITY_FILE}"
echo "✓ tsh login successful"

# Test 2: Kubernetes access
echo "[2/4] Testing kube access..."
"${TOOLS_FOLDER}/tsh" kube login "${INSTALLATION}"
kubectl get nodes --request-timeout=30s
echo "✓ Kubernetes access successful"

# Test 3: Bot token validity
echo "[3/4] Verifying bot tokens..."
if "${TOOLS_FOLDER}/tctl" bots ls | grep -q "^${INSTALLATION}"; then
  echo "✓ Bot ${INSTALLATION} found"
else
  echo "⚠ Warning: Bot ${INSTALLATION} not found"
fi

# Test 4: Basic kubectl operations through Teleport
echo "[4/6] Testing kubectl operations..."
kubectl get namespaces --request-timeout=30s
kubectl get pods -n kube-system --request-timeout=30s | head -5
echo "✓ kubectl operations successful"

# Test 5: teleport-operator health
echo "[5/6] Checking teleport-operator health..."
kubectl get pods -n giantswarm -l app.kubernetes.io/name=teleport-operator --request-timeout=30s
OPERATOR_READY=$(kubectl get pods -n giantswarm -l app.kubernetes.io/name=teleport-operator -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}')
if [[ "${OPERATOR_READY}" == "True" ]]; then
  echo "✓ teleport-operator is healthy"
else
  echo "✗ teleport-operator is not ready"
  exit 1
fi

# Test 6: Verify cluster is registered in Teleport
echo "[6/6] Verifying cluster registration in Teleport..."
if "${TOOLS_FOLDER}/tctl" get nodes | grep -q "${INSTALLATION}"; then
  echo "✓ Cluster ${INSTALLATION} is registered in Teleport"
else
  echo "⚠ Warning: Cluster ${INSTALLATION} not found in Teleport nodes"
fi

echo "=== All connectivity tests passed ==="
exit 0
```

**Prerequisites for this script:**
- A tbot instance running in gazelle-cicdprod that authenticates to the CI Teleport cluster
- The tbot identity stored in a secret (`ci-teleport-identity-output`) in the `tekton-pipelines` namespace
- This requires adding a new tbot deployment or configuring the existing one to also authenticate to CI Teleport

#### 4. Tekton pipeline

```yaml
# tekton-resources/mc-bootstrap/pipelines/teleport-upgrade-test.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: teleport-upgrade-test
  namespace: mc-bootstrap
spec:
  params:
    - name: TELEPORT_CURRENT_VERSION
      type: string
      description: "Current Teleport version (default: production version)"
      # Default should match current production version
    - name: TELEPORT_TARGET_VERSION
      type: string
      description: "Target Teleport version to upgrade to"
    - name: INSTALLATION
      type: string
      description: "MC installation name for testing"
      default: "*goshawk/gmc/goose/goten*"
    - name: KEEP_ENVIRONMENT
      type: string
      description: "Keep environment after test for debugging"
      default: "false"

  tasks:
    - name: deploy-teleport-ci
      taskRef:
        name: trigger-github-workflow
      params:
        - name: repo
          value: "giantswarm/teleport-fleet"
        - name: workflow
          value: "deploy-ci.yaml"
        - name: inputs
          value: '{"teleport_version": "$(params.TELEPORT_CURRENT_VERSION)"}'

    - name: wait-teleport-ready
      taskRef:
        name: wait-for-teleport
      runAfter: [deploy-teleport-ci]

    - name: create-mc
      taskRef:
        name: mc-bootstrap-create
      runAfter: [wait-teleport-ready]

    - name: validate-pre-upgrade
      taskRef:
        name: validate-teleport-connectivity
      runAfter: [create-mc]

    - name: upgrade-teleport
      taskRef:
        name: trigger-github-workflow
      runAfter: [validate-pre-upgrade]
      params:
        - name: inputs
          value: '{"teleport_version": "$(params.TELEPORT_TARGET_VERSION)"}'

    - name: wait-upgrade-complete
      taskRef:
        name: wait-for-teleport
      runAfter: [upgrade-teleport]

    - name: validate-post-upgrade
      taskRef:
        name: validate-teleport-connectivity
      runAfter: [wait-upgrade-complete]

  finally:
    - name: report-results
      taskRef:
        name: slack-notification

    - name: cleanup
      when:
        - input: "$(params.KEEP_ENVIRONMENT)"
          operator: in
          values: ["false"]
      taskRef:
        name: cleanup-teleport-ci
```

### Validation matrix

| Test | Pre-Upgrade | Post-Upgrade | Description |
|------|-------------|--------------|-------------|
| Proxy Login | ✓ | ✓ | `tsh login` to Teleport proxy |
| Kube Access | ✓ | ✓ | `tsh kube login` and `kubectl` commands |
| Bot Tokens | ✓ | ✓ | Verify bot tokens remain valid |
| teleport-operator | ✓ | ✓ | Operator pods healthy, can register clusters |
| teleport-kube-agent | ✓ | ✓ | Agent connected, cluster visible in Teleport |

### Version compatibility considerations

The upgrade testing must validate compatibility across the entire stack. When upgrading from the **current version** to a **target version**, all components in the chain must remain compatible:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Teleport Cluster (current → target)               │
│                    ci.teleport.giantswarm.io                         │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Connects via proxyAddr
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                    Management Cluster (MC)                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐ │
│  │  teleport-operator  │    │  teleport-operator-tbot             │ │
│  │                     │───►│  Authenticates to Teleport cluster  │ │
│  └─────────────────────┘    └─────────────────────────────────────┘ │
│            │                                                         │
│            │ Deploys teleport-kube-agent to WCs                     │
│            ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  teleport-kube-agent                                            │ │
│  │  Registers MC/WC with Teleport cluster                          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Key compatibility points to validate:**
1. teleport-operator's tbot version must be compatible with the Teleport cluster
2. teleport-kube-agent version must be compatible with the Teleport cluster
3. Existing bot tokens must remain valid after upgrade
4. Cluster registrations must persist through the upgrade

### Trigger mechanisms

1. **Manual (PR comment)**: `/run teleport-upgrade-test TELEPORT_TARGET_VERSION=<version>`
   - Example: `/run teleport-upgrade-test TELEPORT_TARGET_VERSION=19.0.0`
2. **Manual (workflow_dispatch)**: GitHub Actions UI with version inputs
3. **Automated (weekly)**: Cron schedule every Friday at 06:00 UTC
   - Automatically fetches the latest stable Teleport version as target
   - Uses current production version as baseline


## Implementation plan

### Part 1: Create Ephemeral Teleport Cluster Infrastructure

Set up all infrastructure components needed to deploy an ephemeral Teleport cluster (`ci.teleport.giantswarm.io`).

**Repository**: `giantswarm/teleport-fleet`

**Subtasks**:

1. **Create Terraform environment for CI cluster**
   - Create `terraform/envs/ci_db/main.tf` and `outputs.tf`
   - Create `terraform/envs/ci_infra/main.tf` and `output.tf`
   - Use cost-optimized instance types (`t3.medium`)
   - Configure DNS zone for `ci.teleport.giantswarm.io`

2. **Create Kubernetes configuration for CI Teleport**
   - Create `kubernetes/envs/ci/Chart.yaml` with shared dependency
   - Add bot tokens for gazelle-cicdprod

3. **Create GitHub OAuth app for CI Teleport**
   - Register OAuth app for `ci.teleport.giantswarm.io`
   - Store credentials in LastPass and GitHub Actions secrets

4. **Update GitHub Actions workflow**
   - Add `ci` to matrix or create separate workflow
   - Add input parameter for `teleport_chart_version` override

5. **Parameterize Teleport version**
   - Add `teleport_chart_version` variable to Terraform
   - Update `eks_teleport_chart.tf` to use variable

6. **Verify component version compatibility**
   - Ensure tbot and teleport-kube-agent versions are compatible with current Teleport cluster
   - Update component versions if necessary

### Part 2: Integrate MC Bootstrap with Ephemeral Teleport

Configure mc-bootstrap to connect ephemeral MCs to the CI Teleport cluster.

**Repositories**: `giantswarm/mc-bootstrap`, `giantswarm/tekton-resources`, `giantswarm/cicd-gitops`

**Subtasks**:

1. **Create MC Bootstrap CI environment configuration**
   - Create `ci/*goshawk/gmc/goose/goten*-teleport-ci/env`
   - Set `TELEPORT_CLUSTER=ci.teleport.giantswarm.io`

2. **Set up tbot identity for CI Teleport authentication**
   - Create bot token in CI Teleport for gazelle-cicdprod (`bot-gazelle-cicdprod-token.yaml`)
   - Deploy tbot in gazelle-cicdprod that authenticates to CI Teleport
   - Store identity in secret `ci-teleport-identity-output` in `tekton-pipelines` namespace
   - This enables non-interactive authentication from Tekton pipelines

3. **Create Teleport connectivity validation script**
   - Create `scripts/validate-teleport-connectivity.sh`
   - Use tbot identity file for non-interactive authentication
   - Test tsh login, kube access, bot tokens, kubectl operations

4. **Add CI Teleport agekey to cicd-gitops**
   - Generate and encrypt agekey for CI environment

5. **Create Tekton pipeline for upgrade testing**
   - Create `teleport-upgrade-test.yaml` pipeline
   - Include all validation and cleanup tasks

6. **Create Tekton trigger for on-demand testing**
   - Create TriggerTemplate for PR comment triggers

### Part 3: Automation, Cleanup, and Documentation

Implement automated testing and resource cleanup.

**Repositories**: `giantswarm/tekton-resources`, `giantswarm/teleport-fleet`

**Subtasks**:

1. **Create weekly upgrade test cronjob**
   - Schedule for Monday morning
   - Fetch latest stable Teleport version

2. **Implement auto-destroy for CI environment**
   - Add cleanup to pipeline finally block
   - Set S3 lifecycle policy (7-day expiration)

3. **Create nightly orphan cleanup job**
   - Destroy CI resources older than 24 hours

4. **Add monitoring and alerting**
   - Slack notifications for test results
   - OpsGenie alert for failures

5. **Create documentation**
   - Document trigger mechanisms
   - Create production upgrade runbook


## Open questions

1. **Should we test downgrade scenarios?**
   - Recommendation: Not initially, add as future enhancement

2. **How long should sessions survive during upgrade?**
   - Need to define SLA for session continuity

3. **Integration with Renovate for automated version bumps?**
   - Could trigger upgrade test when Renovate proposes Teleport update

4. **Should teleport-operator be upgraded alongside Teleport cluster?**
   - Need to determine if upgrade testing should also cover teleport-operator upgrades
   - Consider: test matrix of Teleport cluster version × teleport-operator version

5. **What is the supported version skew between components?**
   - What is the supported version skew between Teleport server and client components (tbot, teleport-kube-agent)?
   - Should component versions be aligned before or as part of upgrade testing?

## Success metrics

| Metric | Target |
|--------|--------|
| Pipeline execution time | < 1 hour|
| False positive rate | < 5% |
| Time to detect upgrade issues | Before production deployment |

## References

- [teleport-fleet repository](https://github.com/giantswarm/teleport-fleet)
- [teleport-operator repository](https://github.com/giantswarm/teleport-operator)
- [mc-bootstrap repository](https://github.com/giantswarm/mc-bootstrap)
- [tekton-resources repository](https://github.com/giantswarm/tekton-resources)
- [Teleport Upgrade Documentation](https://goteleport.com/docs/management/operations/upgrading/)
- [Teleport Version Compatibility](https://goteleport.com/docs/faq/#version-compatibility)

## Appendix: File changes summary

**teleport-fleet:**
- `terraform/envs/ci_db/main.tf` (new)
- `terraform/envs/ci_db/outputs.tf` (new)
- `terraform/envs/ci_infra/main.tf` (new)
- `terraform/envs/ci_infra/output.tf` (new)
- `terraform/modules/infra/variables.tf` (modify)
- `terraform/modules/infra/eks_teleport_chart.tf` (modify)
- `kubernetes/envs/ci/Chart.yaml` (new)
- `kubernetes/envs/ci/values.yaml` (new)
- `kubernetes/envs/ci/templates/bot-gazelle-cicdprod-token.yaml` (new)
- `.github/workflows/ci.yaml` (modify)

**mc-bootstrap:**
- `ci/*goshawk/gmc/goose/goten*-teleport-ci/env` (new)
- `scripts/validate-teleport-connectivity.sh` (new)

**tekton-resources:**
- `mc-bootstrap/pipelines/teleport-upgrade-test.yaml` (new)
- `mc-bootstrap/tasks/validate-teleport-connectivity.yaml` (new)
- `mc-bootstrap/cronjobs/weekly-teleport-upgrade-test.yaml` (new)

**cicd-gitops:**
- `flux/mc-bootstrap/ci-teleport-agekey.yaml` (new)
- `flux/mc-bootstrap/ci-teleport-tbot.yaml` (new) - tbot deployment for CI Teleport auth

**teleport-operator:**
- No code changes required
- Configuration override via mc-bootstrap to set `teleport.proxyAddr=ci.teleport.giantswarm.io:443`
- teleport-operator on test MCs will connect to CI Teleport via values override
