---
creation_date: 2025-11-11
issues:
  - https://github.com/giantswarm/giantswarm/issues/34532
  - https://github.com/giantswarm/giantswarm/issues/34217
  - https://github.com/giantswarm/roadmap/issues/620
last_review_date: 2025-11-11
owners:
  - https://github.com/orgs/giantswarm/teams/team-honeybadger
state: proposed
summary: Move collections to management-cluster-bases, introduce shared-collection and support stages.
---

## Problem Statement

Collections are constantly deploying the latest version of apps inside them. We want to be able to override
versions of apps in different stages.

## Current status

Collections are gitops repositories constantly reconciled with Flux to our management clusters.

Each provider supported by us has its own collection. There are so-called addons collections that are reconciled
separately from the provider collections in selected, hybrid / multi-provider MCs.

Each collection has a Konfiguration CR in them that uses the `management-clusters` KonfigurationSchema to generate
configuration for the apps in them. The schema is located [here](https://github.com/giantswarm/konfiguration-schemas/tree/management-cluster-configuration/v1.0.0/schemas/management-cluster-configuration).

## Goals, non-goals, assumptions

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

### Assumptions

- At the point of migration, App CRs in the collections have been replaced with Flux HelmReleases, that can do
  automatic upgrades to the latest or within a given semversion range, or 

## Design proposal

### New collections layout in MCB

We will demonstrate it via three parts: `shared` -> `capa` -> `capa-asia`, to prove that it could be chained indefinitely.

The core of the problem is that we want to have building blocks that split to stage specific blocks.
Then we want to have other blocks that "inherit" these blocks and also splits further into more specific blocks, and so on.

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

The `shared/stages` folders contain a `Kustomization`, that is in its most minimal form looks like:

```yaml
resources:
  - ../../base
```

#### Capa (provider) collection in details

The `capa` collection `base/kustomization.yaml` is a `Component` that in its most simple form:

- list the manifests beyond the `shared` provider collection that will be included in this collection
- includes a patch to the `Konfiguration` from the base to include further render targets.

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

The `capa/stages` folders contain a `Kustomization`. For the example of a `stable` stages, in its most minimal form looks like:

```yaml
components:
  - ../../base
resources:
  - ../../../shared/stages/stable
```

#### Capa Asia (provider) collection in details

Same as `capa` collection, but in the `stages/kustomization.yaml` files, instead of the `shared` stage bheing included,
the new parent is `capa`, thus in its most basic form - for a `stable` stage - looks like:

```yaml
components:
  - ../../base
resources:
  - ../../../capa/stages/stable
```

### Integration with the Generalized Configuration System (GCS)

Add support for stages as new layers to the `management-cluster-configuration` schema.

Visualization can be found in this diagram: https://miro.com/app/board/uXjVKUVwcLg=/.

#### Setup

`shared-configs`: https://github.com/giantswarm/shared-configs/pull/378
`giantswarm-configs`: https://github.com/giantswarm/giantswarm-configs/pull/387

Clone / checkout `giantswarm-configs` at branch: `introduce-stages`, then run:

```shell
SHARED_CONFIGS_BRANCH=introduce-stages make assemble-config-ssh
```

`konfiguration-schemas`: https://github.com/giantswarm/konfiguration-schemas/pull/1

Clone / checkout `konfiguration-schemas` at branch: `introduce-stages`.

#### Description

Provides:
- default GS specified stages and templates for them shared across all konfiguration rendered for that stage
    - this does not allow setting secret values files cos its in `shared-configs`
- CCR specific stages so per customer stage specific templates can be created
    - this does not allow setting secret values files cos it would mean we need to share a common AGE key across all of that customers MCs (possible tho, just we dont want to)
- the MC specific secret values files must set stage secret template values (error on rendering with that stage otherwise)

#### Structure and where to put what (from e.g. AE perspective)

---

AE: The customer wants to have a configuration for a given app for only one of their MCs.

Answer: Then you don't need stages, just put it into `installations/MC_NAME/apps/APP_NAME` templates.

---

AE: The customer wants to have a value across all their MCs for a given app.

Answer: Then you don't need stages. You need to put the value in all installation app template and the value in the installation value files.

---

AE: The customer wants to have something for all their STAGE_NAME stage cluster for a given app.

Answer: Create the templates for the app in CCR repo `stages/STAGE_NAME/apps/APP_NAME`. CM template file name:
`configmap-values.yaml.template`, Secret template name: `secret-values.yaml.template`. If you want to have
a default value across all MCs, add it to `stages/STAGE_NAME`config.yaml`. Alternatively if you dont want it on all MCs,
you can create an if condition for the value being defined in the template too. You can provide a different value
per MC by setting it in `installations/MC_NAME/config.yaml.patch` Note that secrets must always go under
`installations/MC_NAME/secret.yaml`, you cant define it under the stages folder, because that would
require sharing a decryption key across all customer MCs.

---

AE: I want to have a value for a given app across al customer for a given STAGE_NAME stage.

Answer: Since we talk about all customers now, you must make the change in `shared-configs`, not CCR that is customer-specific.
The templates are in: `default/stages/STAGE_NAME/apps/APP_NAME`. CM template file name: `configmap-values.yaml.template`,
Secret template name: `secret-values.yaml.template`. There is no support for having secret values defined like.
The config map default values for the stage go under `default/stages/STAGE_NAME/apps/APP_NAME/config.yaml`.
You can make the template conditional if you don't want to have it for all MCs. If no default is provided
and no conditions are used, it can result in a rendering error for the missing value if the stage is used to
generate config for an MC. You can also set the value for customer level in the CCR stage value file or per MC.

---

#### Example commands

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

Note that `.b` is overriden here in the `goten` MC config map value file.

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

## Alternative solutions
