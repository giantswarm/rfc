---
creation_date: 2022-06-20
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: approved
---

# Multi layer app configs

## Intro

Our current app delivery mechanism is by using App CRs. Currently, App CRs allow for
[two layers](https://docs.giantswarm.io/tutorials/fleet-management/app-platform/app-configuration/#levels). So far it was good enough to have these 2
layers, but with our introduction of GitOps with Flux, this is starting to be a limiting factor.

Basically, the problem starts when we have more than 2 layers (a base and an override) of configuration in a GitOps
repo. With just 2 layers, the base layer can use `config` part of App CR and the overriding layer can use `userConfig`.
Unfortunately, as soon as we have a 3rd layer, the only choice is to either redefine `config` or `userConfig` entirely,
as there's no other way to achieve this configuration.

Why is it impossible?

1. The `App CR` doesn't have necessary properties - provides only 2 layers.
1. The `ConfigMap` in k8s can have only top-level keys.
1. It is possible to override a single `ConfigMap`'s key with `kustomize`, but
   it doesn't solve the problem, as it's still impossible to override any other key than a top-level one.

## References

- [adidas request ticket](https://github.com/giantswarm/giantswarm/issues/22272)
- limited environment setup in [gitops-template](https://github.com/giantswarm/gitops-template/pull/41)

## User stories

1. As a GitOps user, I want to have as many base layers in my GitOps repo as I want. On each layer, I want to be able to
   override App config with selected keys only and not have to provide a full configuration.
1. As a GitOps user, I want to be able to use setups that come from multiple base layers at once. As an example, I want
   to have a `dev/stage/prod` base that sets app's resources based on deployment stage (by overriding a single
   config key) and I want to have regional bases like `east/west` that configure app's allowed IP ranges (again, by
   overriding another single config property).

## Possible solutions

### Enhancing App CR

We can extend App CR with on optional list of `ConfigMap`/`Secret` objects. Configuration coming from `config:` and
`userConfig:` properties (if given) is applied at the end of this list (to maintain backward compatibility).
`app-operator` does merging of all layers on the list, from top to bottom, instead of just merging the two properties.

This new list is called `extraConfigs`. Each entry in it has a field called the `priority`.
It has a default value assumed that  makes them to be applied before `config` to keep the backward compatibility.
On top of that `config` and `userConfig` gets a priority level - documented in App Platform - as well it becomes
possible to apply some of the `extraConfigs` between the `config` and `userConfig` entries or even after `userConfig`.
The bedrock is still considered to be what is in the catalog. It is not possible to apply `extraConfigs` before that.

The `config` and `userConfig` fields will be kept. The motivation for keeping them and the priority field is that
we have some components in App Platform that does late-binding of config maps and secrets when they are created
after the Application is already deployed. With getting rid of the original fields, having only a list we can not
programmatically tell where to insert the new item in the list. On the other hand if we want to add some overrides
later on without adding it directly to the user overrides we need to have the priorities we can use to set
a high enough number so that the new layer will be applied on top of everything.

#### Merging algorithm

Assuming the following priorities for the platform layers:

- Catalog: A (e.g.: 0)
- Cluster (`config`): B (e.g.: 50)
- User (`userConfig`): C (e.g.: 100)

The distance (d) between each priority level should be the same.
The `priority` field is validated on the CRD schema definition that it must be within range of: `]A, C + d]` and have
the default value of: `A + d / 2` rounded up if necessary.

The merging algorithm is as follows:

1. Configuration from the catalog (A)
2. All entries from `extraConfigs` with priority of P: A < P <= B
3. Configuration from `config` entry (B)
4. All entries from `extraConfigs` with priority of P: B < P <= C
5. Configuration from `userConfig` entry (C)
6. All entries from `extraConfigs` with priority of P: C < P <= C + d

In case of multiple items in `extraConfigs` having the same priority, the order on the list is binding, with the item lower on the list being merged later (overriding those higher on the list).

The idea is modeled after Flux's [HelmRelease configuration](https://fluxcd.io/docs/components/helm/api/#helm.toolkit.fluxcd.io/v2beta1.ValuesReference).

#### Example

With empty config list, works as it was so far:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
spec:
  catalog: giantswarm
  config:
    configMap:
      name: ingress-controller-values
      namespace: m2m01
  configs: []  # <-- new
  name: ingress-nginx
  namespace: kube-system
  userConfig:
    configMap:
      name: ingress-nginx-user-values
      namespace: m2m01
  version: 2.7.0
```

Using some `extraConfigs` with no priority set:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
spec:
   catalog: giantswarm
   config:
      configMap:
         name: ingress-controller-values
         namespace: m2m01
   configs:
      - kind: secret
        name: ingress-nginx-admin-login
        namespace: m2m01
      - kind: configMap
        name: ingress-nginx-admin-account
        namespace: m2m01
   name: ingress-nginx
   namespace: kube-system
   userConfig:
      configMap:
         name: ingress-nginx-user-values
         namespace: m2m01
   version: 2.7.0
```

In the above example the order for config maps will be:

1. Catalog (P = 0)
1. ConfigMap: ingress-nginx-admin-account (P = 25)
1. ConfigMap: ingress-controller-values (P = 50)
1. ConfigMap: ingress-nginx-user-values (P = 100)

And for secrets it is simply (because not cluster or user layer is defined):

1. Catalog
1. Secret: ingress-nginx-admin-login

And an example with some `priority` fields set on `extraConfigs` entries:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
spec:
   catalog: giantswarm
   config:
      configMap:
         name: ingress-controller-values
         namespace: m2m01
   configs:
      - kind: configMap
        name: ingress-nginx-post-user
        namespace: m2m01
        priority: 125
      - kind: configMap
        name: ingress-nginx-pre-user
        namespace: m2m01
        priority: 75
      - kind: configMap
        name: ingress-nginx-pre-cluster
        namespace: m2m01
      - kind: configMap
        name: ingress-nginx-final
        namespace: m2m01
        priority: 125
      - kind: configMap
        name: ingress-nginx-high-priority
        namespace: m2m01
        priority: 10
   name: ingress-nginx
   namespace: kube-system
   userConfig:
      configMap:
         name: ingress-nginx-user-values
         namespace: m2m01
   version: 2.7.0
```

The merge order for config maps will be:

1. Catalog (P = 0)
1. ConfigMap: ingress-nginx-high-priority (P = 10)
1. ConfigMap: ingress-nginx-pre-cluster (P = 25)
1. ConfigMap: ingress-controller-values (P = 50)
1. ConfigMap: ingress-nginx-pre-user (P = 75)
1. ConfigMap: ingress-nginx-app-user-values (P = 100)
1. ConfigMap: ingress-nginx-post-user (P = 125, position in the list: 1)
1. ConfigMap: ingress-nginx-final (P = 125, position in the list: 4)

#### Pros

- solves the problem everywhere, in App CR and in GitOps
- backward compatible
- easy to implement
- makes `app-operator` more like `helm-controller` from Flux, which may make replacing `chart-operator` with it easier

#### Cons

- we're solving a problem already solved in Flux's `HelmRelease`
- we have to implement it

### Implementing ConfigMap key merging in `kustomize`

Currently, `kustomize` can't merge keys within a `ConfigMap`. Still, this is a 'wanted' feature. We might just
implement this in `kustomize`.

#### Pros

- solves the problem for GitOps
- fame and glory in the community for implementing a needed feature
- getting to know `kustomize`'s code base

#### Cons

- we have to implement it on an unknown code base - might be a bigger challenge
- this solves the problem for GitOps only (well, any tool using `kustomize`)

### Drop App CR and switch to HelmRelease

This seems unrealistic, as we really a lot on app platform and its features. Still, bypassing App CR in GitOps
scenario would solve the problem.

#### Pros

- we don't implement anything in code

#### Cons

- this might mean phasing out app platform operators or living in two worlds (with and without app platform)
- App CRs and app-platform are deeply integrated into our product, we can't get rid of it easily

### Dropping the 'values' key in AppCR's CMs/Secrets and moving them to top level

The idea is change this layout of App CR's ConfigMap:

```yaml
data:
  values: |-
    key1:
      subkey1: val1
      subkey2: val2
    key2:
      subkey1: val7
      props:
        p1: 7
        p2: 3
```

to this one

```yaml
data:
  key1: |-
    subkey1: val1
    subkey2: val2
  key2: |-
    subkey1: val7
    props:
      p1: 7
      p2: 3
```

So to skip the `values` key and use top-level keys directly.

#### Pros

- very easy to implement in backward compatible way

#### Cons

- enables only top-level key merging, so it's not a real generic solution
