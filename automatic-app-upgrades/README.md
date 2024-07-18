---
creation_date: 2022-04-15
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: obsolete
summary: Use Flux's watch features such as `ImagePolicy` to automatically upgrade to newer app versions. This change was not performed, but we use `*-collection` repos (on MCs) and cluster default apps (on MCs/WCs) instead, so this RFC is obsolete.
---

# Automatic App upgrades

## Solution proposal

We propose to use OCI registries, Flux controllers, and GitHub repositories to fully automate App upgrades. This also
includes anything delivered as Apps, including app bundles and CAPI clusters delivered as apps.

## Relevant resources

- RFC [automatic cluster upgrades](../automatic-cluster-upgrades/README.md)
- the whole [gitops-template](https://github.com/giantswarm/gitops-template/) repo
  - in particular the [auto upgrades page](https://github.com/giantswarm/gitops-template/blob/main/docs/apps/automatic_updates_appcr.md)
- ticket: [automated cluster upgrades](https://github.com/giantswarm/giantswarm/issues/21419)
- ticket: overarching issue for [automatic app updates](https://github.com/giantswarm/giantswarm/issues/20641)
- ticket: issue for [upgrade testing](https://github.com/giantswarm/giantswarm/issues/20640)
- ticket for [customer vs GS responsibility during upgrades](https://github.com/giantswarm/giantswarm/issues/21419)

## Motivation

We would like to automate App upgrades. Since CAPI clusters will be packaged as Apps as well, this would, by extension, allow us to automate their upgrades as well. This would serve our customers, as well as unblock some of the epics and stories, like pull-based app collections.

## Solution in detail

Use OCI registries to hold Helm charts. Use GitOps, in particular Flux's [Image Automation Controllers](https://fluxcd.io/docs/components/image/), to monitor the registry and upgrade apps when a newer version of the chart is pushed.

Since version 3.8.0, Helm [enables storing charts in OCI registries](https://helm.sh/blog/storing-charts-in-oci/). OCI registries, or Open Containers Initiative registries, allow storing arbitrary artifacts other than containers in them using a common storage standard.

One of the registries that are fully conformant with the OCI specification is Azure Container Registry. The registry we currently use as a mirror or backup to our other registries. This is why in the first iteration of implementation we will be using Azure Container Registry as our default OCI registry.

We are currently using CircleCI to publish Helm charts to designated GitHub repositories we call Catalogs. Both `app-operator` and `chart-operator` can browse the Catalogs and pull App charts to install them in the cluster. Since their respective versions [v5.9.0](https://github.com/giantswarm/app-operator/blob/master/CHANGELOG.md#590---2022-04-07) and [v2.21.0](https://github.com/giantswarm/chart-operator/blob/master/CHANGELOG.md#2210---2022-04-07) both those operators can interact with OCI-based Catalogs as well.

Flux operators, specifically Image Reflector Controller and Image Automation Controller, can monitor image registries for new tags. Then, based on automation rules, they can update Git repositories by making commits to a specified branch. This allows us to monitor OCI registries and update Git repositories with a new version automatically.

We could set up rules for Flux controllers to update App CRs in a repository whenever a new chart version (matching the automation rule) is pushed to the Azure Container Registry. Then Flux GitOps controllers would see the update in the repository and apply it to the cluster, effectively updating the App CR with the new version. All of this would be triggered automatically after a new release is crafted for any of the apps. The updated App version would be committed to the branch watched by GitOps controllers so that the update happens automatically.

We acknowledge some of the Apps could have specific requirements regarding versioning, be it freezing the version, following just one major release's minors and patches, etc. It is solvable by having a custom automation setting, as permitted by [ImagePolicy's Policy section](https://fluxcd.io/docs/components/image/imagepolicies/#policy). For example:

### A policy following latest stable version

```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=1.0.0'
```

### A policy following minors and patches of v1.x.x

```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'
```

### A policy following patches of v3.7.x

```yaml
kind: ImagePolicy
spec:
  policy:
    semver:
      range: '>=3.7.0 <3.8.0'
```

More examples are presented in [the documentation](https://fluxcd.io/docs/components/image/imagepolicies/#examples).

![Graph showcasing the described solution](https://user-images.githubusercontent.com/4587658/163184967-d8fa5e6b-18ac-42e5-bf6c-7fd8e7df3ab6.png)

## Automated upgrades release process summary

The release process with upgrades as described above looks like this:

1. App part
   1. A team responsible for the app prepares a new app branch for the release
   1. The new App Chart CR is tested for successful [upgrade using `ats`](https://github.com/giantswarm/app-test-suite#quick-start)
   1. The App is released, the chart has to be put into OCI repository (already supported by `architect-orb`)
1. GitOps configuration part
   1. Customer has prepared GitOps repository, including bases (they don't have to be bases, they can be individual clusters/apps, but we're encouraging bases for better (re)usability) that make sense for grouping their infrastructure (Honeybadger is working on specific layout recommendations)
   1. Each base has defined upgrade strategy - a range of versions that can be automatically set for this part of repo. Check [gitops-template](https://github.com/giantswarm/gitops-template/blob/main/docs/apps/automatic_updates_appcr.md#app-cr-version-field-mark)
   1. When a new App Chart is detected in the OCI registry, every cluster that uses the base (or just has a proper version range defined) is upgraded to a newer version. The upgrade might mean that Flux will just push the detected change to a separate upgrade branch in the repo and from there a human operator will be required to create a PR (can be easily automated) and approve it.

## Future work

As mentioned previously, `app-operator` and `chart-operator` are ready to interact with OCI registries. Various registry providers have been tested as part of [OCI registry support for App Platform](https://github.com/giantswarm/roadmap/issues/391) issue. The viability of the proposed solution has been tested and confirmed as [a part of the same issue](https://github.com/giantswarm/roadmap/issues/391#issuecomment-1096522248).

The remaining bits:

- Setting up a repository holding App CRs
- Setting up automation and rules in a repository
- Configuring Flux to reconcile both of the above mentioned repositories
- Updating CI to push Helm charts to the AzureCR as well
