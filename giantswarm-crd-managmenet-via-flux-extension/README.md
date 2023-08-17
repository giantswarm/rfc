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

### Each MC has their own `crds` kustomization

Just like each management cluster in each CMC repository has a `managmenet-clusters/<MC_NAME>/catalogs` kustomization.
We have the same convention for `flux-extras` and `crossplane-providers` as an additional example.

We follow this pattern and each can references their own set of CRDs they want to install before everything else.

Since all CAPIx are the same, and they don't need special stuff they can reference the `all` one from MCB.

For vintage, we can prepare the provider specific CRDs, and they just need to be referenced where needed.

#### Pros

- We already do something like this with catalogs and actually flux-extras abd crossplane too. We set the convention
  that something needs to exist at a specific location which is good UX guidance and support wise too.
- Provides customers a nice extension point
- Easy to use, very generic solution
- Easy to implement (maybe some hassle with `auto_branches` as always)

#### Cons

- Needs the usual patch in the `flux` kustomization to point to the MC specific path in the CMC.
  For example: https://github.com/giantswarm/giantswarm-management-clusters/blob/c3fdb97382bed3585b48bdce8ed074f23ba5a8f7/management-clusters/giraffe/kustomization.yaml#L12-L44
- Maybe a bit of boilerplate in CMC repos

### Unique `crds` kustomization per MCB `bases/provider` via new MCB flux source

Instead of a concrete, single `crds` Flux kustomization resource there is rather a convention that we have one
called `crds`. Then each provider in MCB under `bases/provider` is responsible to create it.

For this to work we need a new MCB Flux source that is optimally deployed to all clusters, tho for this issue
itself we can just deploy it to vintage clusters. However, there are already some other use cases where
having the MCB source in the cluster could be utilized like triggering reconciliation immediately on e.g. `flux`
kustomization when MCB changes.

Related links to reconciliation trigger by different source workaround:

- https://github.com/giantswarm/management-cluster-bases/compare/main...experiment-with-trigger
- https://github.com/giantswarm/giantswarm/issues/27597#issuecomment-1632630001

#### Pros

- Sort of drop-in and implicit for customers (tho this can be interpreted as a con too in some use cases)
- We probably need the MCB source soon anyway

#### Cons

- We take away control and the extension point from customers
- Complex and leads to some duplication in MCB repository

### Sidestep - Handle Vintage provider specific CRDs from new `crds-vintage` kustomization

In MCB we create a new Flux kustomization for the vintage providers that point to a k8s kustomization in MCB
that lists the resources stored in the respective `helm/crds-<PROVIDER>` folder in `apiextensions`.

#### Pros

- Easier to implement, smaller impact
- Isolated to work on an extension to vintage clusters only, which also makes it easier to clean up later
- We probably need the MCB source soon anyway

#### Cons

- Not a generic solution, if CAPx clusters need something like this in the future
- A new Flux kustomization is added to vintage clusters and this means a new dependency to `flux` kustomization too
