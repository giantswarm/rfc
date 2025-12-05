---
creation_date: 2025-11-11
issues:
- https://github.com/giantswarm/giantswarm/issues/34532
- https://github.com/giantswarm/giantswarm/issues/34217
- https://github.com/giantswarm/roadmap/issues/620
last_review_date: 2025-11-11
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: Move collections to management-cluster-bases, introduce shared-collection and support stages.
---

# Move collections to management-cluster-bases, introduce shared collection and support stages

## Problem Statement

Collections are constantly deploying the latest version of apps inside them. We want to be able to override
versions and configurations of apps in different stages.

## Current status

Collections are GitOps repositories constantly reconciled with Flux to our management clusters.

Each provider supported by us has its own collection (e.g., capa-app-collection). There are so-called addons collections that are reconciled
separately from the provider collections in selected, hybrid / multi-provider MCs (e.g., https://github.com/giantswarm/vsphere-aws-addons-app-collection).

Each collection has a Konfiguration CR in it that uses the `management-clusters` KonfigurationSchema to generate
configuration for the apps in it. The schema is located [konfiguration-schemas repository](https://github.com/giantswarm/konfiguration-schemas/tree/management-cluster-configuration/v1.0.0/schemas/management-cluster-configuration).

## Assumptions

At the point of migration, App CRs in the collections have been replaced with Flux HelmReleases, that can do
automatic upgrades to the latest or within a given semversion range. This means that the `push-to-app-collection`
CircleCI workflow is no longer needed.

## Goals and non-goals

### Goals

- Get rid of separate collection repositories (provider collections and addon collections as well) and move them all to MCB.
- Introduce shared-collection for provider collections to reduce duplications.
- Support stages for collections.
  - Support patching all manifests inside collections per provider and per stages.
  - Support generating different konfiguration per stages.
- Get rid of `push-to-app-collection` CircleCI workflow (see the Assumptions section).

### Non-goals

- Automatic promotion / propagation of any kind, be it patches or konfiguration.
- Automatic upgrades of apps in collections.

## Design proposal

### New collections layout in MCB

We will demonstrate it via three parts: `shared` -> `capa` -> `capa-asia`, to prove that it could be chained indefinitely.

The core of the problem is that we want to have building blocks that split into stage-specific blocks.
Then we want to have other blocks that "inherit" these blocks and also split further into more specific blocks, and so on.

We think it is not possible to do this without [Kustomize Components](https://kubectl.docs.kubernetes.io/guides/config_management/components/),
and to be more specific because of this [design decision](https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/1802-kustomize-components#proposal):

> A kustomization that is marked as a Component has basically the same capabilities as a normal kustomization. The main distinction is that they are evaluated after the resources of the parent kustomization (overlay or component) have been accumulated, and on top of them. This means that:
>
> - A component with transformers can transform the resources that an overlay has previously specified in the resources field. Components with patches do not have to include the target resource in their resources field.
> - Multiple components can extend and transform the same set of resources sequentially. This is in contrast to overlays, which cannot alter the same base resources, because they clone and extend them in parallel.

A component with transformers can transform the resources that an overlay has previously specified in the `.resources` field.
Components with patches do not have to include the target resource in their `.resources` field. Multiple components can
extend and transform the same set of resources sequentially. This is in contrast to overlays, which cannot alter
the same base resources because they clone and extend them in parallel.

Thus, it is using this behavior of components rather than being actually reusable parts, so to say, what components are
normally intended for.

The following is the proposed layout of the collections in MCB (can be found [here](https://github.com/giantswarm/management-cluster-bases/pull/325)),
with the following legend:

> (KS) means that this `kustomization.yaml` MUST be a Kustomization
> (COMP) means that this `kustomization.yaml` MUST be a Component

```
bases/collections
├── shared
│   ├── base
│   │   ├── app-admission-controller.yaml
│   │   ├── konfiguration.v2.yaml
│   │   ├── kustomization.yaml (KS)
│   │   ├── ...
│   └── stages
│       ├── stable
│       │   └── kustomization.yaml (KS)
│       └── testing
│           └── kustomization.yaml (KS)
├── capa
│   ├── base
│   │   ├── alloy-gateway.yaml
│   │   ├── capa-iam-operator.yaml
│   │   ├── ...
│   │   ├── kustomization.yaml (COMP)
│   │   └── patches
│   │      └── konfiguration.v2.yaml
│   └── stages
│       ├── stable
│       │   └── kustomization.yaml (KS)
│       └── testing
│           └── kustomization.yaml (KS)
├── capa-asia
│   ├── base
│   │   ├── hello-world.yaml
│   │   ├── kustomization.yaml (COMP)
│   │   └── patches
│   │       └── konfiguration.v2.yaml
│   └── stages
│       ├── stable
│       │   └── kustomization.yaml (KS)
│       └── testing
│           └── kustomization.yaml (KS)
├── ...
```

#### Shared (provider) collection in details

The `shared` collection `base/kustomization.yaml` is a `Kustomization` that simply lists all the manifests that will
be part of all provider collections.:

```yaml
resources:
- app-admission-controller.yaml
- konfiguration.v2.yaml
# ...
```

This base is then split first into stages under the `stages` folder.

> It is a must to not share a root folder between the base and the stages, e.g., the root folder contains the base folders
> contents, and then there is a folder in it for stages, for technical reasons how `kustomize` works. Thus, the structure
> is `shared/base` and `shared/stages`.

The `shared/stages/[STAGE_NAME]` folders contain a `Kustomization`, that is in its most minimal form looks like:

```yaml
patches:
  # This is used to patch in the stage variable for all child collections, and thus, render the stage specific konfiguration.
  - target:
      kind: Konfiguration
      name: collection-konfiguration
      namespace: giantswarm
    patch: '[{"op": "add", "path": "/spec/targets/defaults/variables/-", "value": {"name": "stage", "value": "STAGE_NAME"}}]'
resources:
  - ../../base
```

#### Capa (provider) collection in details

The `capa` collection `base/kustomization.yaml` is a `Component` that in its most simple form:

- lists the manifests beyond the `shared` provider collection that will be included in this collection
- includes a patch for the `Konfiguration` object, included from the base (`capa/base`), to add new render targets for apps added in this stage.

```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component
patches:
  - path: patches/konfiguration.v2.yaml
resources:
- alloy-gateway.yaml
- capa-iam-operator.yaml
# ...
```

The `capa/stages/[STAGE_NAME]` folders contain a `Kustomization`. For  example, the `stable` stage, in its most minimal form, looks like:

```yaml
components:
  - ../../base
resources:
  - ../../../shared/stages/stable
```

#### Capa Asia (provider) collection in details

Same as `capa` collection, but in the `stages/kustomization.yaml` files, instead of the `shared` stage being included,
the new parent is `capa`, thus in its most basic form - for a `stable` stage - looks like:

```yaml
components:
  - ../../base
resources:
  - ../../../capa/stages/stable
```

#### Note on addon collections

Addon collections are one-off collections, thus they are not inheriting from a shared base.

They will be structured like the `shared` collection, with a `base` and a `stages` folder.

They have their own `Konfiguration` CR and are reconciled by their own separate Flux `Kustomization`.

#### Usage examples

*Question*: How to add a new manifest to all provider collections?

*Answer*: Add the manifest to the `shared` collection's `base` folder and reference it in `kustomization.yaml`.

---

*Question*: How to make a change for a manifest for a given stage across all provider collections?

*Answer*: Add a patch in `shared/stages/STAGE_NAME`. Either as a separate file e.g., in a `patches` sub folder
and reference it in `kustomization.yaml` or in the `kustomization.yaml` directly. For example, to pin the `sloth-rules`
HelmRelease version for the `testing` stage across all provider collections, add this to the `shared/stages/testing/kustomization.yaml`:

```yaml
patches:
  - target:
      kind: App
      name: sloth-rules
      namespace: giantswarm
    patch: '[{"op": "replace", "path": "/spec/version", "value": "1.1.1"}]'
```

*Question*: How to make a change for a manifest for all stages for a specific provider collection, let's say `capa`?

*Answer*: Add the patch to the `capa/base/kustomization.yaml` folder. If this is a manifest from `shared`, this patch
will be applied on top of those patches, thus creating an override for this provider only for all stages. For example:

```yaml
patches:
  - target:
      kind: App
      name: sloth-rules
      namespace: giantswarm
    patch: '[{"op": "replace", "path": "/spec/version", "value": "2.2.2"}]'
```

---

*Question*: How to make a change for a manifest for a given stage for a specific provider collection, let's say `capa` and `testing`?

*Answer*: Let's stay with the `sloth-rules` example, add the patch to the `capa/stages/testing/kustomization.yaml`:

```yaml
patches:
  - target:
      kind: App
      name: sloth-rules
      namespace: giantswarm
    patch: '[{"op": "replace", "path": "/spec/version", "value": "3.3.3"}]'
```

This will hide the `2.2.2` version patch from the `capa/base/kustomization.yaml` and apply the `3.3.3` patch on top of it,
but only for the `testing` stage. For `stable` stage, the `2.2.2` patch will stay on top.

---

*Question*: So this can be chained indefinitely. Could you give me an overview of the override order?

*Answer*: In this example, from bottom to top (so the one further down the list will take final effect):

- `shared/base`
- `shared/stages/STAGE_NAME`
- `capa/base`
- `capa/stages/STAGE_NAME`
- `capa-asia/base`
- `capa-asia/stages/STAGE_NAME`

And so on, can be chained indefinitely. So its always the most ancient parent base first, then the given stage from that,
then iterate on this through the chain up to the top collection.

---

*Question*: Can I add manifest just for a given collection and only for a given stage, let's say `capa` and `testing`?

*Answer*: Sure, why not? Add the manifests to the `capa/stages/testing` folder and reference them in the`kustomization.yaml` there.

#### Examples

##### Setup

Clone / checkout `management-cluster-bases` at branch: `stages-experiment`.

##### The sloth-rules example overrides walkthrough

Let's see through the overrides of the above `sloth-rules` example:

```shell
# This is the very base
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/shared/base | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
0.46.1

# No overrides, inherits shared base
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/shared/stages/stable | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
0.46.1

# We have an override for the testing stage. All child collections will inherit this change for this stage and this manifest.
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/shared/stages/testing | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
1.1.1

# This is component, won't work (well it could, but there is no guarantee and after all these are not meant to be used on their own!)
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/capa/base | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
Error: no resource matches strategic merge patch "Konfiguration.v1alpha1.konfigure.giantswarm.io/collection-konfiguration.giantswarm": no matches for Id Konfiguration.v1alpha1.konfigure.giantswarm.io/collection-konfiguration.giantswarm; failed to find unique target for patch Konfiguration.v1alpha1.konfigure.giantswarm.io/collection-konfiguration.giantswarm

# We have an override in capa/base but capa/stages/stable does not have one, so it inherits that. Hides the default from shared/base.
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/capa/stages/stable | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
2.2.2

# We have an override in capa/stages/testing, so it overrides the override from capa/base that overrode shared/stages/testing.
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/capa/stages/testing | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
3.3.3

# This is inherited from capa/base.
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/capa-asia/stages/stable | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
2.2.2

# We have an override in capa-asia/stages/testing, so it overrides the override from capa/stages/testing that overrode capa/base, that overrode shared/base.
$ kustomize build --load-restrictor LoadRestrictionsNone bases/collections/capa-asia/stages/testing | yq 'select(.metadata.name == "sloth-rules") | .spec.version'
4.4.4
```

### Integration with the Generalized Configuration System (GCS)

We need to add support for stages as new layers to the `management-cluster-configuration` schema in order to be able to
generate different konfiguration per stages.

Visualization can be found in this diagram: https://miro.com/app/board/uXjVKUVwcLg=/.

#### Structure

The following is the proposed layout of `shared-configs` and CCR repository structures, with the following legend:

> (NEW) means this is a new addition to the structure

```
default
├── apps
│   ├── app-operator
│   ├── ...
├── config.yaml
├── stages (NEW)
│   ├── stable
│   │   ├── apps
│   │   │   └── app-operator
│   │   │       ├── configmap-values.yaml.template
│   │   │       └── secret-values.yaml.template
│   │   └── config.yaml
│   └── testing
│       ├── apps
│       │   └── app-operator
│       │       └── configmap-values.yaml.template
│       └── config.yaml
installations
├── golem
│   ├── apps
│   │   ├── dex-app
│   │   │   ├── configmap-values.yaml.patch
│   │   │   └── secret-values.yaml.patch
│   ├── config.yaml.patch
│   └── secret.yaml
stages (NEW)
├── stable
│   ├── apps
│   │   └── app-operator
│   │       ├── configmap-values.yaml.template
│   │       └── secret-values.yaml.template
│   └── config.yaml
└── testing
    ├── apps
    │   └── app-operator
    │       └── configmap-values.yaml.template
    └── config.yaml
```

This provides:
- default, GS specified stages and templates shared across all konfiguration rendered for that stage
    - this does not allow setting secret values files cos its in `shared-configs` (because we would need to share a common AGE key across all customer's MCs)
- CCR specific stages so per customer stage specific templates can be created
    - this does not allow setting secret values files cos it would mean we need to share a common AGE key across all of those customer's MCs (possibly though, just we don't want to)
- the MC specific secret values files must set stage secret template values (error on rendering with that stage otherwise)

#### Changes to the management-cluster-configuration schema

It can be found at: https://github.com/giantswarm/konfiguration-schemas/pull/1.

First, we add a new optional `stage` variable. By making it optional, we can omit it and thus end up with the good old
management-cluster-configuration rendering, as the stages templates will be considered empty, thus doing nothing.

```yaml
variables:
  # ...
  - name: stage
    required: false
    default: none
  # ...
```

The first new layer is the `default-stages` layer, which is added before the `default` layer so it can override defaults
for given stages for all customers.

```yaml
layers:
  # ...
  # After the `default` layer, we add the shared, `default-stages` layer.
  - id: default-stages
    path:
      directory: default/stages
      required: false
    # Notice we do not allow secret value files here because we do not want to share a common AGE key across all customers.
    # Secret values referenced in the secret templates MUST be set in the MC specific secret values file or the templates:
    # written in a way that the value is optional.
    values:
      path:
        directory: << stage >>
        required: false
      configMap:
        name: config.yaml
        required: false
    templates:
      path:
        directory: << stage >>/apps/<< app >>
        required: false
      configMap:
        name: configmap-values.yaml.template
        required: false
        values:
          merge:
            strategy: ConfigMapsInLayerOrder
      secret:
        name: secret-values.yaml.template
        required: false
        values:
          merge:
            strategy: SecretsInLayerOrder
  # ...
```

The next, CMC level stages layer is after `default-stages` and before `management-cluster` layer, so CMCs can override
the shared default and stages layers, but they can still be overridden for given installations in the `management-cluster` layer.

```yaml
layers:
  # After the `default-stages` layer, we add the CMC specific `stages` layer.
  - id: stages
    path:
      directory: stages
      required: false
    # Notice we do not allow secret value files here because we do not want to share a common AGE key across all MCs of the customer.
    # Secret values referenced in the secret templates MUST be set in the MC specific secret values file or the templates:
    # written in a way that the value is optional.
    values:
      path:
        directory: << stage >>
        required: false
      configMap:
        name: config.yaml
        required: false
    templates:
      path:
        directory: << stage >>/apps/<< app >>
        required: false
      configMap:
        name: configmap-values.yaml.template
        required: false
        values:
          merge:
            strategy: ConfigMapsInLayerOrder
      secret:
        name: secret-values.yaml.template
        required: false
        values:
          merge:
            strategy: SecretsInLayerOrder
```

#### Setup

`shared-configs`: https://github.com/giantswarm/shared-configs/pull/378
`giantswarm-configs`: https://github.com/giantswarm/giantswarm-configs/pull/387

Clone / checkout `giantswarm-configs` at branch: `introduce-stages`, then run:

```shell
SHARED_CONFIGS_BRANCH=introduce-stages make assemble-config-ssh
```

`konfiguration-schemas`: https://github.com/giantswarm/konfiguration-schemas/pull/1

Clone / checkout `konfiguration-schemas` at branch: `introduce-stages`.


#### Usage examples

*Question*: I want to have a value for a given app across all customers for a given STAGE_NAME stage.

*Answer*: Since we talk about all customers now, you must make the change in `shared-configs`, not CCR that is customer-specific.
The templates are in: `default/stages/STAGE_NAME/apps/APP_NAME`. CM template file name: `configmap-values.yaml.template`,
Secret template name: `secret-values.yaml.template`. There is no support for having secret values defined like.
The config map default values for the stage go under `default/stages/STAGE_NAME/apps/APP_NAME/config.yaml`.
You can make the template conditional if you don't want to have it for all MCs. If no default is provided
and no conditions are used, it can result in a rendering error for the missing value if the stage is used to
generate config for an MC. You can also set the value for customer level in the CCR stage value file or per MC.

---

*Question*: The customer wants to have something for all their STAGE_NAME stage cluster for a given app.

*Answer*: Create the templates for the app in CCR repo `stages/STAGE_NAME/apps/APP_NAME`. CM template file name:
`configmap-values.yaml.template`, Secret template name: `secret-values.yaml.template`. If you want to have
a default value across all MCs, add it to `stages/STAGE_NAME/config.yaml`. Alternatively if you don't want it on all MCs,
you can create an if condition for the value being defined in the template too. You can provide a different value
per MC by setting it in `installations/MC_NAME/config.yaml.patch` Note that secrets must always go under
`installations/MC_NAME/secret.yaml`, you cant define it under the stages folder, because that would
require sharing a decryption key across all customer MCs.

#### Examples

With no `stage` defined (or it could be set to a `none` or a something that does not exist):

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/golem.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=golem" \
  --variable "app=app-operator" \
  --raw
```

The `app-operator` in stage `testing` for `golem`:

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/golem.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=golem" \
  --variable "app=app-operator" \
  --variable="stage=testing" \
  --raw
```

The `app-operator` in stage `stable` for `golem`:

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/golem.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=golem" \
  --variable "app=app-operator" \
  --variable="stage=stable" \
  --raw
```

Try changing the `installation` for the above 2 commands to `goten` and observe the difference (if any):

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/goten.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=goten" \
  --variable "app=app-operator" \
  --variable="stage=testing" \
  --raw
```

and:

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/goten.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=goten" \
  --variable "app=app-operator" \
  --variable="stage=stable" \
  --raw
```

Note that `.b` is overridden here in the `goten` MC config map value file.

Now observe for `glippy`:

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/glippy.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=glippy" \
  --variable "app=app-operator" \
  --variable="stage=testing" \
  --raw
```

and that the `stable` fails because the default stages secret templates defines the usage of the stage certificate data, but the `glippy` installation secret values does not set it:

```shell
SOPS_AGE_KEY_FILE=$UMBRELLA_TARGET_DIR/secrets/glippy.sops.age.key konfigure render \
  --schema $GOPATH/src/github.com/giantswarm/konfiguration-schemas/schemas/management-cluster-configuration/schema.yaml \
  --dir $UMBRELLA_TARGET_DIR/ccr/giantswarm-configs \
  --variable "installation=glippy" \
  --variable "app=app-operator" \
  --variable="stage=stable" \
  --raw
```

It fails there first as of layer order, but note that fixing that is not enough, cos `glippy` does not define the `.stableStage.secret` either that is defined at the CCR customer level of stages.

Please note that the variables are not in any ways tied to real Giant Swarm or whatever "app" names. These can eb anything.
If you want multiple flavors or kinds of konfiguration for an "app", go for it. Create `app-operator-snowflake` or `app-operator-unique` and `app-operator-workload-cluster`, it will work.

### Putting it all together

There are a few more things we need to make it all work:

- some apps in collections use our Flux-based CRD distribution (`crds` kustomization), thus we need some solution for this
- we need a way to tell for each management cluster in CMC repos, which provider and stage (sometimes same for addon collections) it should use
  - with [remote patches being broken starting Flux 2.5](https://github.com/fluxcd/kustomize-controller/issues/1544), we need another way to do this

#### The CRD problem and possible solutions

There are CRDs we distribute via the `crds` kustomization for apps that are part of collections.
For example, at [this](https://github.com/giantswarm/management-cluster-bases/blob/4b70cebfcbebd53bbefd45cce60b0663e147c82b/bases/crds/giantswarm/kustomization.yaml)
point in MCB:

- `app-operator`
- `konfigure-operator`
- `silence-operator`
- `organization-operator`
- `rbac-operator`
- `observability-operator`

We need to make sure that these CRDs are installed in the management cluster before the apps that use them. But now we
also need stages for them. Unfortunately, CRDs are not good for patching; you apply the whole manifest.

Thus, the most straightforward approach - can be checked out [here](https://github.com/giantswarm/management-cluster-bases/tree/stages-experiment/bases/crds/giantswarm)
is to live with some code duplication here. To do this, let's split the `crds` base in MCB like this:

```
bases/crds
├── common-flux-v2
│   └── kustomization.yaml
│   └── stages
│       └── ...
├── flux-app-v2
│   └── kustomization.yaml
│   └── stages
│       └── ...
└── giantswarm
    ├── kustomization.yaml
    └── stages
        ├── stable
        │   └── kustomization.yaml
        └── testing
            ├── app-platform
            │   └── kustomization.yaml
            ├── konfigure-operator
            │   └── kustomization.yaml
            ├── kustomization.yaml
            ├── observability-bundle
            │   └── kustomization.yaml
            ├── organization-operator
            │   └── kustomization.yaml
            ├── rbac-operator
            │   └── kustomization.yaml
            ├── releases
            │   └── kustomization.yaml
            └── silence-operator
                └── kustomization.yaml
```

This could be a backward compatible solution and allow to avoid some code duplication. Let's look at it in details
at the `bases/crds/giantswarm` example. The `common-flux-v2` and `flux-app-v2` ones are more simple and a bit special.

First, we should keep the `bases/crds/giantswarm/kustomization.yaml` for the backward compatibility, assuming that the
testing stage would have the same result as the current state. Would look like:

```yaml
resources:
  - stages/testing
```

The `stages/testing/kustomization.yaml` would look like this:

```yaml
resources:
  - app-platform
  - konfigure-operator
  - observability-bundle
  - organization-operator
  - rbac-operator
  - releases
  - silence-operator
```

Then each of these sub paths would contain the actual CRDs for that given operator, for example, the `konfigure-operator`
folder's `kustomization.yaml` would look like this:

```yaml
resources:
  - https://raw.githubusercontent.com/giantswarm/konfigure-operator/refs/tags/v1.0.1/config/crd/bases/konfigure.giantswarm.io_konfigurationschemas.yaml
  - https://raw.githubusercontent.com/giantswarm/konfigure-operator/refs/tags/v1.0.1/config/crd/bases/konfigure.giantswarm.io_konfigurations.yaml
```

This gives us some code reusability in other stages, for example `stable`, but allowing us to reference some
parts when they are the same, and create a new subfolder for parts with references to the different CRDs when
there is a difference between stages. Thus, the `base/crds/giantswarm/stages/stable/kustomization.yaml`
would look like this, when it reuses / matches the `testing` stage exactly:

```yaml
resources:
  - ../testing/app-platform
  - ../testing/konfigure-operator
  - ../testing/observability-bundle
  - ../testing/organization-operator
  - ../testing/rbac-operator
  - ../testing/releases
  - ../testing/silence-operator
```

If let's say `konfigure-operator` is different, then we create `konfigure-operator` folder with a `kustomization.yaml`
file that looks like this:

```yaml
resources:
  - https://raw.githubusercontent.com/giantswarm/konfigure-operator/refs/tags/<<ANOTHER_VERSION>>/config/crd/bases/konfigure.giantswarm.io_konfigurationschemas.yaml
  - https://raw.githubusercontent.com/giantswarm/konfigure-operator/refs/tags/<<ANOTHER_VERSION>>/config/crd/bases/konfigure.giantswarm.io_konfigurations.yaml
```

and the `base/crds/giantswarm/stages/stable/kustomization.yaml` would change to:

```yaml
resources:
  - ../testing/app-platform
  # Use it from this stage with <<ANOTHER_VERSION>>
  - konfigure-operator
  - ../testing/observability-bundle
  - ../testing/organization-operator
  - ../testing/rbac-operator
  - ../testing/releases
  - ../testing/silence-operator
```

#### Using the new collections in CMCs and migration steps

We should use the above structure the same way we do it for `crds`, `catalogs`, `flux-extras` as remote bases.

Let's create a standard entrypoint for the collection `Kustomization` with a single `kustomization.yaml` file.

```
management-clusters
├── golem
│   ├── catalogs
│   │   └── kustomization.yaml
│   ├── collections
│   │   └── kustomization.yaml
│   ├── extras
│   │   └── kustomization.yaml
│...
```

This file should reference the remote bases, normally the provider base, but hybrid clusters will reference the addon
collections here as well. So in a most simple form it will look like this:

```yaml
resources:
  - https://github.com/giantswarm/management-cluster-bases//bases/collections/capa/stages/testing?ref=stages-experiment
```

or with an addon collection, it would look like this:

```yaml
resources:
  - https://github.com/giantswarm/management-cluster-bases//bases/collections/capa/stages/testing?ref=stages-experiment
  - https://github.com/giantswarm/management-cluster-bases//bases/collections/vsphere-aws-addons/stages/testing?ref=stages-experiment
```

This approach has a lot of benefits:

- the `collection` Kustomization source will change to the CMC source (`management-clusters-fleet`)
- each management cluster gains the ability to provide their own overrides, changes to collections if needed
- will use the same method as other parts of CMC repos which simplifies testing / devs can apply the same methods
- we cut the number of Flux kustomizations by 1 in the case of hybrid clusters, as the same kustomizations will reconcile addon collections as well
- we cut the number of Flux sources too by 1, as we don't need the collection repo source anymore, but most importantly, using the same source makes testing easier, by not needing to update / align multiple ones in complex scenarios

##### Implications and migration steps

One implication is that we have patches to Kyverno and Prometheus Operator in MCB on the `collections` Kustomization
itself. Since these apply to all collections, these MUST be moved to the shared collection. They dont even need to be
patches anymore. Since collections contain raw, pure manifests, change them directly.

They are located here: https://github.com/giantswarm/management-cluster-bases/blob/4b70cebfcbebd53bbefd45cce60b0663e147c82b/bases/flux-giantswarm-resources/resource-kustomizations.yaml#L96-L124

The migration needs to be done in 2 steps, but only hybrid clusters need both of them.

Please note that this was not fully tried, unlike all of the above, so the actual migration might slightly differ.
This is to give a rough idea / thought through about the potential complexity of the migration.

First, let's see how to migrate the provider collections.

- prepare the `collections/kustomization.yaml` entrypoints in CMC repos for each MC. Decide which stage to use for each MC.
- we need two things in the root `kustomization.yaml` for each MC to start with:
  - first we need a full patch for the path and the source of the `Kustomization`, to point it to
    `managment-clusters/MC_NAME/collections` and the source to `management-clusters-fleet`. We will remove these later
    when the KS changes in MCB with the usual replacement:
    ```yaml
    replacements:
    - source:
      kind: ConfigMap
      name: management-cluster-metadata
      namespace: flux-giantswarm
      fieldPath: data.NAME
      targets:
        - select:
          kind: Kustomization
          name: collections
          namespace: flux-giantswarm
          fieldPaths:
            - spec.path
          options:
            delimiter: "/"
            index: 2
      ```
- the `bases/provider` folders in MCB each contain a `patch-collection-gitrepository.yaml` file. We will need to clean
  these up, but they should not be in the way of the migration, as when switching, we will not use the `collection`
  git repository Flux source anymore.

Second, let's see how addon collections work now to understand how they are different.

Addon collections have a separate extras base in MCB that contains their own `Kustomization` and `GitRepository` sources.

```
extras
├── vsphere-addons
│   ├── gitrepository-vsphere-addons-collection.yaml
│   ├── kustomization-vsphere-addons-collection.yaml
│   └── kustomization.yaml
├── vsphere-aws-addons
│   ├── gitrepository-vsphere-aws-addons-collection.yaml
│   ├── kustomization-vsphere-aws-addons-collection.yaml
│   └── kustomization.yaml
```

Then these are referenced in the hybrid MC root `kustomization.yaml` file like:

```yaml
resources:
  - https://github.com/giantswarm/management-cluster-bases//extras/vsphere-aws-addons?ref=main
```

The rough approach for the migration:

- these Kustomizations have prune enabled, so we need to disable that
- we need to suspend these sources and kustomizations (either in MCB with the above step or manually)
- we remove the reference to the `extras` remote base from the MC `kustomization.yaml`
- we add the new `collections` remote base to the MC `collections/kustomization.yaml`
- the `collections` Kustomization will now reconcile the addon collections
- clean up the old addon collection source and kustomization

## Alternative solutions

### The most simple solution

Most of the work here comes from moving the collections to MCB repo and introducing the `shared` collection.

90% of the above can be achieved by introducing stages in-place in the currently existing collection repositories.

See: https://github.com/giantswarm/capa-app-collection/pull/100.

For this to use we simply need to patch which path (stage) to use CMC repos and it is also backward compatible by keeping
the original `kustomization.yaml` in place.
