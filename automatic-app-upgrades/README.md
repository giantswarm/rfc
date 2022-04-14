# Automatic App upgrades

## Solution proposal

We propose to use OCI registries, Flux controllers, and GitHub repositories to fully automate App upgrades.

## Motivation

We would like to automate App upgrades. Since CAPI clusters will be packaged as Apps as well, this would, by extension, allow us to automate their upgrades as well. This would serve our customers, as well as unblock some of the epics and stories, like pull-based app collections.

## Solution in detail

Use OCI registries to hold Helm charts. Use GitOps, in particular Flux's [Image Automation Controllers](https://fluxcd.io/docs/components/image/), to monitor the registry and upgrade apps when a newer version of the chart is pushed.

Since version 3.8.0, Helm [enables storing charts in OCI registries](https://helm.sh/blog/storing-charts-in-oci/). OCI registries, or Open Containers Initiative registries, allow storing arbitrary artifacts other than containers in them using a common storage standard.

One of the registries that are fully conformant with the OCI specification is Azure Container Registry. The registry we currently use as a mirror or backup to our other registries. This is why in the first iteration of implementation we will be using Azure Container Registry as our default OCI registry.

We are currently using CircleCI to publish Helm charts to designated GitHub repositories we call Catalogs. Both `app-operator` and `chart-operator` can browse the Catalogs and pull App charts to install them in the cluster. Since their respective versions [v5.9.0](https://github.com/giantswarm/app-operator/blob/master/CHANGELOG.md#590---2022-04-07) and [v2.21.0](https://github.com/giantswarm/chart-operator/blob/master/CHANGELOG.md#2210---2022-04-07) both those operators can interact with OCI-based Catalogs as well.

Flux operators, specifically Image Reflector Controller and Image Automation Controller, can monitor image registries for new tags. Then, based on automation rules, they can update Git repositories by making commits to a specified branch. This allows us to monitor OCI registries and update Git repositories with a new version automatically.

We could set up rules for Flux controllers to update App CRs in a repository whenever a new chart version (matching the automation rule) is pushed to the Azure Container Registry. Then Flux GitOps controllers would see the update in the repository and apply it to the cluster, effectively updating the App CR with the new version. All of this would be triggered automatically after a new release is crafted for any of the apps.

We acknowledge some of the Apps could have specific requirements regarding versioning, be it freezing the version, following just one major release's minors and patches, etc. It is solvable by having a custom automation setting, as permitted by [ImagePolicy's Policy section](https://fluxcd.io/docs/components/image/imagepolicies/#policy). For example:

**A policy following latest stable version**
```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=1.0.0'
```

**A policy following minors and patches of v1.x.x**
```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'
```

**A policy following patches of v3.7.x**
```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=3.7.0 <3.8.0'
```

More examples are presented in [the documentation](https://fluxcd.io/docs/components/image/imagepolicies/#examples).

![Graph showcasing the described solution](https://user-images.githubusercontent.com/4587658/163184967-d8fa5e6b-18ac-42e5-bf6c-7fd8e7df3ab6.png)

## Future work

As mentioned previously, `app-operator` and `chart-operator` are ready to interact with OCI registries. Various registry providers have been tested as part of [OCI registry support for App Platform](https://github.com/giantswarm/roadmap/issues/391) issue. The viability of the proposed solution has been tested and confirmed as [a part of the same issue](https://github.com/giantswarm/roadmap/issues/391#issuecomment-1096522248).

The remaining bits:
- Setting up a repository holding App CRs
- Setting up automation and rules in a repository
- Configuring Flux to reconcile both of the abovementioned repositories
- Updating CI to push Helm charts to the AzureCR as well
