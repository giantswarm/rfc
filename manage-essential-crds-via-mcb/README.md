# Manage essential CRDs via MCB

Essential CRDs are widely used ones by all / most of Giant Swarm apps in MCs, like VPA or Service Monitors.

## Context

We are currently managing CRDs for MCs in many ways:

- For Flux, we install it with MCB and Flux manages it for itself
  - https://github.com/giantswarm/management-cluster-bases/tree/9170ca4d74e5564ff85d5260a281dab03f94a297/bases/flux-app/crds
  - https://github.com/giantswarm/management-cluster-bases/blob/9170ca4d74e5564ff85d5260a281dab03f94a297/bases/tools/Makefile.custom.mk#L50C12-L50C15 + https://github.com/giantswarm/mc-bootstrap/blob/bddf059f13a1f7733dc34ed1f9276522bc263a87/scripts/setup-cmc.sh#L36-L45
- For giantswarm CRDs it still uses opsctl
  - https://github.com/giantswarm/mc-bootstrap/blob/bddf059f13a1f7733dc34ed1f9276522bc263a87/scripts/install-giantswarm-crds.sh
  - https://github.com/giantswarm/opsctl/tree/d27dd026532fe10e2d1146c8db8ae9bf915d240b/command/ensure/crds
- For VPA there is a separate chart for CRDs:
  - https://github.com/giantswarm/mc-bootstrap/blob/bddf059f13a1f7733dc34ed1f9276522bc263a87/scripts/install-vpa-crds.sh
- For kyverno it clones the given revision of the repo and applies the CRDs:
  - https://github.com/giantswarm/mc-bootstrap/blob/bddf059f13a1f7733dc34ed1f9276522bc263a87/scripts/install-kyverno-crds.sh

Additionally, we have ATS via `apptestctl` that needs to be updated every time a new CRD becomes essential and this
solution uses `curl` and `kubectl` apply to get teh job done:

- https://github.com/giantswarm/apptestctl/blob/90942be9c1c2fd58f765bc191d8ef5889717eb4b/hack/sync-crds.sh

### Related tickets / blocked issues

- https://github.com/giantswarm/giantswarm/issues/27558
- https://github.com/giantswarm/flux-app/pull/209
- https://github.com/giantswarm/roadmap/issues/2480

### Related experiment pull requests

- https://github.com/giantswarm/management-cluster-bases/pull/28/files
- https://github.com/giantswarm/giantswarm-management-clusters/pull/138/files

## Proposed solution

I propose to manage at least the Giant Swarm CRDs in MCB in the following structure and this also sets up the
infrastructure to manage any other CRDs the same way without additional changes in CMC repos.

```text
bases/crds
├── all
│   └── kustomization.yaml
├── flux-app
│   ├── crds.yaml
│   └── kustomization.yaml
└── giantswarm
    └── kustomization.yaml
```

Where `flux-app` we already have, we just move it up from `bases/flux-app/crds/kustomization.yaml` to `bases/crds`.

The `giantswarm` one is new and as a start would look like :

```yaml
resources:
  - https://raw.githubusercontent.com/giantswarm/apiextensions-application/master/config/crd/application.giantswarm.io_appcatalogentries.yaml
  - https://raw.githubusercontent.com/giantswarm/apiextensions-application/master/config/crd/application.giantswarm.io_appcatalogs.yaml
  - https://raw.githubusercontent.com/giantswarm/apiextensions-application/master/config/crd/application.giantswarm.io_apps.yaml
  - https://raw.githubusercontent.com/giantswarm/apiextensions-application/master/config/crd/application.giantswarm.io_catalogs.yaml
  - https://raw.githubusercontent.com/giantswarm/apiextensions-application/master/config/crd/application.giantswarm.io_charts.yaml
```

But it could be anything that kustomize can actually handle, for example for `vertical-pod-autoscaler-crd` could look like:

```yaml
helmCharts:
  - name: vertical-pod-autoscaler-crd
    includeCRDs: false
    namespace: giantswarm
    repo: https://giantswarm.github.io/control-plane-catalog/
    releaseName: vertical-pod-autoscaler-crd
    version: v2.0.1
```

It is not perfect for `prometheus-operator-crd` as that Chart contains a lot more CRDs than what we currently consider
essential:

- https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/example/prometheus-operator-crd/monitoring.coreos.com_servicemonitors.yaml
- https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/example/prometheus-operator-crd/monitoring.coreos.com_podmonitors.yaml

As with `kustomize` we can patch delete some of those CRDs from the rendered Helm chart, but that is an exclude list
instead of an allow list, therefor needs more maintenance. However, I think pre-installing all the CRDs in this Chart
in order to avoid this issue is fine too.

Or for `cilium` we do not have a Chart, but could use the remote resources approach like:

```yaml
resources:
  - https://raw.githubusercontent.com/cilium/cilium/main/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml
  - https://raw.githubusercontent.com/cilium/cilium/main/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumclusterwidenetworkpolicies.yaml
```

Finally, `bases/crds/all` is the part that makes it easy to extend at later point only in MCB. It would look like this:

```yaml
resources:
  - ../flux-app
  - ../giantswarm
  # ...
```

As a result of the above `all` kustomization, we should rename `flux-crds` kustomization to `crds`.

### Solving mc-bootstrap

For `flux` CRDs we currently have a `make` command exposed in the shared Makefile: https://github.com/giantswarm/management-cluster-bases/blob/9170ca4d74e5564ff85d5260a281dab03f94a297/bases/tools/Makefile.custom.mk#L50
and in `mc-bootstrap` we call that to render all the CRDs and we simply `kubectl` apply them. Then when `flux` is all
set up on the MC it will take them over managing them.

We introduce these new targets in this shared Makefile - and remove the old `build-flux-app-crds`:

```Makefile
BUILD_CRD_TARGETS := build-all-crds build-bootstrap-crds build-flux-app-crds build-giantswarm-crds

# This is where the original `build-flux-app-crds` is removed from (+ the matching .PHONY)
BUILD_FLUX_APP_TARGETS := build-flux-app-customer build-flux-app-giantswarm

.PHONY: $(BUILD_CRD_TARGETS)
build-all-crds:  ## Builds https://github.com/giantswarm/management-cluster-bases//bases/crds/all
build-bootstrap-crds:  ## Builds https://github.com/giantswarm/management-cluster-bases//bases/crds/bootstrap
build-flux-app-crds:  ## Builds https://github.com/giantswarm/management-cluster-bases//bases/crds/flux-app
build-giantswarm-crds:  ## Builds https://github.com/giantswarm/management-cluster-bases//bases/crds/giantswarm
$(BUILD_CRD_TARGETS): $(KUSTOMIZE) ## Build CRDs
	@echo "====> $@"

	rm -rf /tmp/mcb.${MCB_BRANCH}
	git clone -b $(MCB_BRANCH) https://github.com/${BASE_REPOSITORY} /tmp/mcb.${MCB_BRANCH}

	mkdir -p output

	$(KUSTOMIZE) build --load-restrictor LoadRestrictionsNone /tmp/mcb.${MCB_BRANCH}/bases/crds/$(subst build-,,$(subst -crds,,$@)) -o output/$(subst build-,,$(subst -crds,,$@))-crds.yaml
```

Then we can do the `make build-XYZ-crds` in `mc-bootstrap` for the given CMC and simply `kubectl` apply them for `flux`
to take over when it is bootstrapped.

### Solving for apptestctl

Same as `mc-bootstrap`. Additionally, we might need to make sure that the executor running the ATS has access to:

- `make`, obviously
- `git`, probably already satisfied

We don't need to worry about `kustomize` or `yq` as the Makefile downloads these as a dependency to the targets.

## Migration process

### Renamed flux-crds kustomization to crds

Since `prune` is false - right?! - we can do this in the following steps:

- in CMCs, update `bases/flux-app/crds/kustomization.yaml`. This is the current one used by `flux-crds` kustomization,
  should be updated to:
  ```yaml
  resources: []
  ```
- in CMCs, add `bases/crds/kustomization.yaml` with contents of (of course change `ref` when testing):
  ```yaml
  resources:
  - https://github.com/giantswarm/management-cluster-bases//bases/crds/all?ref=main
  ```
- in MCB update the `flux-crds` kustomization to be called `crds` and make it point to `path: "./bases/crds"` instead of
  `path: "./bases/flux-app/crds"`
  ```yaml
  name: "crds"
  path: "./bases/flux-app/crds"
  ```

### Update build scripts

Beyond adding the new targets to build the CRDs as shown above, the `ensure-versions` target in MCB needs to be updated
to point to the new local cache folder of Flux CRDs. (Tho with the proxy in better state in CN cluster we could try to
go back to remote resources as well, could also be done separately.)

### Considerations for Giant Swarm CRDs

None, I think we should definitely do this and as an extra win we can remove `opsctl ensure crds` for good and our
CRDs will be rolled out much faster too from now on.

### Considerations for Chart managed CRDs

I think the best would be to manage all of these essential CRDs the same way. We can use `kustomize` helm chart
rendering as shown above for using the same method. This adds the flux labels fine to the already existing resources,
but it makes no sense to keep them as Helm charts, so purging the releases should be done manually by KEEEPing existing
resource either via `"helm.sh/resource-policy": keep` annotation (could be added via flux then removed later),
see [docs](https://helm.sh/docs/howto/charts_tips_and_tricks/#tell-helm-not-to-uninstall-a-resource) or simply deleting
the related secrets used by Helm.

Note, that Flux helm releases do not work here for multiple reasons:

- flux is not up at this point
- currently it is not possible to render Flux helm releases to manually apply the resources
