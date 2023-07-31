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
