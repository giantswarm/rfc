# Automated upgrades with GitOps

## Assumptions

- we're using FluxCD
- this doc takes into account only Apps - anything that is installed using App CR
- for the mechanism described here, charts must be stored in an OCI registry

## Relevant resources

- the whole [gitops-template](https://github.com/giantswarm/gitops-template/) repo
  - in particular the [auto upgrades page](https://github.com/giantswarm/gitops-template/blob/main/docs/apps/automatic_updates_appcr.md)
- ticket: [automated cluster upgrades](https://github.com/giantswarm/giantswarm/issues/21419)
- ticket: overarching issue for [automatic app updates](https://github.com/giantswarm/giantswarm/issues/20641)
- ticket: issue for [upgrade testing](https://github.com/giantswarm/giantswarm/issues/20640)
- ticket for [customer vs GS responsibility during upgrades](https://github.com/giantswarm/giantswarm/issues/21419)

## The upgrade process overview

1. App part
   1. A team responsible for the app prepares a new app branch for the release
   1. The new App Chart CR is tested for successful [upgrade using `ats`](https://github.com/giantswarm/app-test-suite#quick-start)
   1. The App is released, the chart has to be put into OCI repository (already supported by `architect-orb`)
1. GitOps configuration part
   1. Customer has prepared GitOps repository, including bases (they don't have to be bases, they can be individual clusters/apps, but we're encouraging bases for better (re)usability) that make sense for grouping their infrastructure (Honeybadger is working on specific layout recommendations)
   1. Each base has defined upgrade strategy - a range of versions that can be automatically set for this part of repo. Check [gitops-template](https://github.com/giantswarm/gitops-template/blob/main/docs/apps/automatic_updates_appcr.md#app-cr-version-field-mark)
   1. When a new App Chart is detected in the OCI registry, every cluster that uses the base (or just has a proper version range defined) is upgraded to a newer version. The upgrade might mean that Flux will just push the detected change to a separate upgrade branch in the repo and from there a human operator will be required to create a PR (can be easily automated) and approve it.
