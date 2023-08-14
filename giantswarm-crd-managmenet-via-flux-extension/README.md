# Extension to Giant Swarm CRD management via Flux

Related to: [Manage essential CRDs via MCB](../manage-essential-crds-via-mcb/README.md)

## Context

The original solution does not leave room for provider specific resources in the sense that all `crds` 
Flux kustomization reconciles CMC `bases/crds` meaning all management clusters in the given CMC will
have the same set of CRDs installed. (Note, that with the current solution we need to have a file in the CMC
that is pointed to by the `crds` kustomization because the flux source is the CMC repository and from there
we point to the remote resources in MCB.)

This is normal for CAPx based management clusters as their specific CRDs are managed in a different way
in [cluster-api-app](https://github.com/giantswarm/cluster-api-app/tree/e3f45963d98705302a2ef3855695fa9abb583c41/helm/cluster-api/files/core/bases)
and in `mc-bootstrap` we install the common set of Giant Swarm CRDs to all CAPx clusters.

For vintage clusters however there are provider specific CRDs located in
[apiextensions](https://github.com/giantswarm/apiextensions/tree/44bee19e76387be141de42398587b4af0da9edda/helm)
for `aws`, `azure` and `kvm`.

## Solutions

### Unique `crds` kustomization per MCB `bases/provider` via new MCB flux source

...

### Sidestep - Handle Vintage provider specific CRDs from new `crds-vintage` kustomization

In MCB we create a new Flux kustomization for the vintage providers that point to a k8s kustomization in MCB
that lists the resources stored in the respective `helm/crds-<PROVIDER>` folder in `apiextensions`.

For this to work we need a new MCB Flux source that is optimally deployed to all clusters, tho for this issue
itself we can just deploy it to vintage clusters. However, there are already some other use cases where
having the MCB source in the cluster could be utilized like triggering reconciliation immediately on e.g. `flux`
kustomization when MCB changes.

Related links to reconciliation trigger by different source workaround:

- https://github.com/giantswarm/management-cluster-bases/compare/main...experiment-with-trigger
- https://github.com/giantswarm/giantswarm/issues/27597#issuecomment-1632630001

#### Pros

- Easier to implement, smaller impact
- Isolated to work on an extension to vintage clusters only, which also makes it easier to clean up later
- We probably need the MCB source soon anyway

#### Cons

- Not a generic solution, if CAPx clusters need something like this in the future
- A new Flux kustomization is added to vintage clusters and this means a new dependency to `flux` kustomization too
