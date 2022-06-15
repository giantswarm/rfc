# Multi layer app configs

## Intro

Our current app delivery mechanism is by using App CRs. Currently, App CRs allow for
[two layers](https://docs.giantswarm.io/app-platform/app-configuration/). So far it was good enough to have these 2
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
  name: nginx-ingress-controller-app
  namespace: kube-system
  userConfig:
    configMap:
      name: nginx-ingress-controller-app-user-values
      namespace: m2m01
  version: 2.7.0
```

Using the new list instead of `config` and `userConfig`, works exactly the same as the one above:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
spec:
  catalog: giantswarm
  configs:  # <-- new
    - kind: configMap
      name: ingress-controller-values
      namespace: m2m01
    - kind: configMap
      name: nginx-ingress-controller-app-user-values
      namespace: m2m01
  name: nginx-ingress-controller-app
  namespace: kube-system
  version: 2.7.0
```

Using the new list only and referencing more than 2 objects:

```yaml
apiVersion: application.giantswarm.io/v1alpha1
kind: App
spec:
  catalog: giantswarm
  configs:  # <-- new
    - kind: configMap
      name: ingress-controller-values
      namespace: m2m01
    - kind: configMap
      name: nginx-ingress-controller-app-user-values
      namespace: m2m01
    - kind: secret
      name: nginx-ingress-controller-admin-login
      namespace: m2m01
    - kind: configMap
      name: nginx-ingress-controller-admin-account
      namespace: m2m01
  name: nginx-ingress-controller-app
  namespace: kube-system
  version: 2.7.0
```

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
