---
creation_date: 2025-12-11
issues:
  - https://github.com/giantswarm/giantswarm/issues/24237
last_review_date: 2025-12-15
owners:
  - https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary:
  We want to use flux and flux-operator's automatic upgrades capabilities to create automatic upgrades for
  different release stages, so we don't have to manually or through extra automation care about those
  rollouts.
---

# Using semVer tags for automatic app upgrades in different release stages

## Introduction

Flux can automatically detect and apply new releases of a Helm Chart as new tags for the configured chart are
created in the OCI repository. These upgrades can be based on matching the semVer tag as both a semVer range
and a regexp to match. We can use
[semVer tags, tag ranges and regexp filters](https://fluxcd.io/flux/components/source/ocirepositories/#reference)
to decide which tags will be considered for the automatic upgrade and which won't.

Using this feature and combining it with a defined tagging schema will allow us to create a process, where a
developer drives automatic upgrades for specific release stages by just assigning git tags of specific format
to Helm Chart releases. No configuration with the deployment tools will be required.

This RFC serves three related purposes:

1. Proposing proper semVer-compatible tagging for our software releases
2. Demonstrating how to use these tags with Flux's automatic upgrade capabilities. The automatic upgrade
   functionality depends on adhering to the proposed tagging process, but the mechanism itself is provided by
   Flux and works with any semVer-compatible tags.
3. Discussing with our developers what is the set of tagging schemas they find appropriate.

### Scope and context

The proposed tagging schema and conventions described in this RFC apply specifically to software developed and
maintained by Giant Swarm. This RFC does not propose enforcing any tagging requirements on customer software.
We want to offer the underlying mechanism (semVer-based automatic upgrades using Flux) to everyone, including
customers, who can use it with their own tagging schemes. However, the specific tag formats (`-dev.*`,
`-rc.*`, etc.) and the workflow described here are intended for Giant Swarm's internal release engineering
process. The main goal of applying this scheme is to achieve auto-upgrade capabilities for our managed apps
and cluster apps.

This RFC establishes the semVer tagging foundation that enables more advanced features. We're currently in
planning or evaluation of more tools that will integrate with core Flux features and will also require semVer
tagging. Only as a context, please know that we're evaluating the following tools:

- **Flux Operator with ResourceSets**: Already available and committed to, this will provide:
  - Grouping resources into deployment units (replacing bundles with enhanced templating)
  - Dependencies between cluster objects
  - Conditional deployments
  - CEL evaluation of target cluster resources
  - Scheduled upgrades for cluster apps

- **Sveltos**: Currently in early evaluation, this could provide:
  - Gated deployments
  - Dynamic deployments based on target cluster tags
  - Event-based deployments

The current RFC focuses on the foundational tagging scheme and basic automatic upgrade usage, which is an
embedded feature of flux. The advanced features above will be covered in separate RFCs as they mature.

## General idea

As an example, if we want an app to be automatically deployed and patched as soon as a new patch release is
available (let's assume this is a valid behavior for a stable stage), we can configure the automatic upgrade
semVer for the app to the `X.Y.*`, where "X" and "Y" are set to specific values, and the `*` means that any
patch release will be automatically deployed. That way we can automatically deliver fixes for an app
(including security) without manually configuring the cluster to select and app version to run.

Now, if we want to expand this idea to multi-stage deployments, we can configure different stages with
different semVer expressions. For example:

- "dev", deploy any version of an app that matches tag `*-dev.*`
- "testing", deploy any version of an app that matches tag `*-rc.*`
- "stable-32", deploy any version of the app that matches tag `>=32.0.0` (this excludes `-*` tags, so
  pre-releases)

We can use this mechanism for any `HelmRelease` or `ResourceSet` object that is created on an MC, for any
object deployed to a local (MC) or a remote (WC) cluster. The proposed solution will result in "commitless
gitops workflow", where the version of an app to deploy is deterministic, but is calculated dynamically based
on the semVer expression stored in the deployment object (possibly coming from a gitops repo) and from the set
of tags discovered in an OCI registry. The specific version of a chart to deploy will be calculated
dynamically and will not be stored in the gitops repo.

## Use cases

As Giant Swarm engineers:

- We want to have our app releases automatically applied to different MCs, so that we can test them over
  longer runs. We want to group our MCs into stages, where we automatically upgrade first testing, then our
  stable MCs, only then customers (just an example).
- We want automatic rollouts, so that a new release of app is applied automatically, without further manual
  configuration, but only to selected MCs.
- This also includes any apps deployed to WCs, as long as they are defined on an MC. This means that we can
  use this with our customers to let them test pre-releases of the giant swarm maintained software.
- Customers can test pre-release versions (e.g., RC releases) of Giant Swarm maintained software by
  configuring their app deployments to accept the appropriate tag range (e.g., `*-rc.*` for RC versions). This
  can be done for individual apps or en-masse using tools like Kustomize patches, depending on the customer's
  deployment approach. This allows customers to test our pre-releases without requiring commits or PR
  approvals just to get an updated version.
- This covers also time-restricted/scheduled upgrades, if they come from `flux-operator`.

## Out of scope use cases

The following are right now considered out of scope of the current work, but still valid for the future:

- dependency management other than the one Flux already offers for HelmReleases
- advanced health checking of the target cluster
- promotion tools: allowing a change (accepted tags configuration) to be propagated from 1 release channel to
  another in an automated way
  - use case: upgrading customer's WCs by release channel, gated and accepted by a user

## Implementation

### Overview

We will introduce strict opinionated tagging patterns, then will assign acceptable tag ranges and regexp
matchers to clusters of specific release stage. We propose a starting set of tags and matching rule, but they
can be easily extended or modified in the future.

### Implementation idea

We will use `flux-operator` and `helm-controller` abilities to discover tags in remote OCI repositories using
the new recommended `OCIRepository` object. Tags matching the configured semVer expression will be applied to
related `ResourceSets` or `HelmReleases`. Each release channel will provide tag acceptance criteria for the
set of deployed apps (mostly `collections`), where each app will define its own accepted semVer expression for
tags.

To be able to use SemVer tags for this, we will need to enhance our CICD tooling to make the proposed git
tagging schema easier to use by the developers. The proposed schema is backward compatible for stable
releases, but adds and optional 'Release Candidate' stage and fixes the dev builds tagging, which right now is
not semVer compliant.

Proposed default tagging schema:

- For the "stable" release, we keep the current tagging schema with tags matching `[0-9]+\.[0-9]+\.[0-9]+`
  (ie. `1.9.1`)
- For the "release candidate" stage, we introduce a new tag according to the recommended way of semVer
  tagging: `rc` suffixed tags matching `[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+` (ie. `1.9.2-rc.1`)
- For `dev` builds, we want to build every commit of a non-`main` branch a developer is working on. We need to
  make this builds to have a tag that allows to identify the branch it is coming from and to make them
  sortable according to semVer. The proposed schema is thus
  `[0-9]+\.[0-9]+\.[0-9]+-dev\.(branch)\.[0-9]{8}\.[0-9]{6}` where `branch` is the name of the branch the
  build is coming from and the suffix is a time stamp with date and time parts. For example, if the last
  stable tag in history is `1.9.1` and the branch name is `my-feature-1`, the build results in a tag like
  `1.9.2-dev.my-feature.20260127.094959`.

The default matching scheme for apps deployed to our MCs is:

- For `stable`, we use stable tags for all apps, so `*` semVer expression. If preferred, this can be limited
  by the app owner to be limit to a subset of stable releases, like `1.x.x` or `1.2.x`. In that case, upgrades
  beyond minor or patch version will require a reconfiguration of the match expression by the owner.
- For `stable-testing`, we use the newest stable or RC tag available for each app.
- For `testing`, we use by default the same tag matching as for `stable-testing`. App developers, that want to
  test a dev release of an app they are working on, will reconfigure the app's expression to match the dev
  builds of the branch they are working on. This will match the behaviour we have in the `reservations`
  channel. As an example, a dev working on a `my-feature` branch of app `X` will reconfigure, as part of the
  reservation process, the app's accepted range on the chosen `testing` MC from the default `*-rc.*` to
  `*-dev.my-feature.*`. The change will have to be reversed once the testing is done. As this is a multi-step
  process prone to human error, we will provide a tool to execute it in one go.

**Note on tag format flexibility:** The RFC proposes `stable`, `rc`, and `dev` as the default solution we
should use. Still, the naming of tags and the configuration of accepted tags on app deployment won't be
limited in any way and will allow app owners to introduce new tag schemas and match expressions, if they need
to do so. Owners can also configure the match expression to match 1 tag exactly, effectively disabling any
auto-upgrade on the app.

The above tagging and matching schemas mean that the deployed version of an application will entirely depend
on the set of semVer tags available in a remote OCI registries. In other words, developers decide where a
specific version of an app will be deployed by assigning tags to releases they create.

This approach is flexible enough to support multiple stages on the same workload cluster in different
namespaces, as each deployment configuration is independent and can specify its own semVer expression.

### Implementation steps

1. We implement changes in our CICD process, so the tagging schema is easy to follow.
1. We set the accepted semVer ranges for the apps in each stage. To avoid manually setting ranges for each
   existing app, we can use the patching feature of `Kustomizations` and - for example - patch the version of
   every deployed HelmRelease to the correct default value for this stage, ie. a testing cluster deployment
   sets and app version to `*-rc.*` by default.

### CICD process changes

To make creating necessary artifact tags easier, we want to extend our CI/CD tooling for GitHub in the
following way:

1. We keep the current `main#release#[patch,minor,major]` logic, that will now create tags that are considered
   stable releases.
1. We add new `main#release#[patch-rc,minor-rc,major-rc]` logic, that will bump the selected part of the tag,
   but create a next RC tag for it. Examples:
   1. `1.2.3` + `main#release#patch-rc` = `1.2.4-rc.1`
   1. `1.2.3` + `main#release#minor-rc` = `1.3.0-rc.1`
   1. `1.2.3` + `main#release#major-rc` = `2.0.0-rc.1`
   1. `1.2.3-rc.1` + `main#release#patch-rc` = `1.2.3-rc.2`
1. We stop using `X.Y.Z-commit_hash` for dev builds. The tags of this form are not semVer compatible and will
   result in incorrect sorting of tags.
1. The above will be replaced with the following automation:
   1. For each branch named `[NAME]` other than `main`, every commit in this branch will by default trigger a
      build that will be tagged `X.Y.X-dev.NAME.DATE.TIME`. Examples for a branch named `my-feature`:
      1. A new commit in a new branch `my-feature` + last commit in the parent tree is `1.2.3` =
         `1.2.4-dev.my-feature.20260112.120959`
   1. If the branch name starts with the `nobuild/` prefix, builds are not automatically triggered, but a
      release can still be created by manually assigning a correct tag. This allows us to save resources on
      the build pipeline, OCI storage and release auto-upgrade processes.
      1. Example: there's a branch `nobuild/i-dont-care` and a developer creates a tag `1.2.3-dev.awesome.1`:
         the build is triggered and pushed to the OCI registry.

## Example developer's workflows and the related release process

Let's assume we have 3 release stages: dev, testing and prod. Each of them is assigned to a group of clusters
and configures a separate set of semVers for apps.

### "stable" stage

Each app in this release stage is configured to deploy only stable releases, with tags matching `X.Y.Z`, like
`2.0.0`. Each time a new stable release of any of the apps is created on GitHub, the build succeeds and a new
chart is uploaded to the OCI registry and the app is automatically deployed to matching clusters. We can limit
this to patch releases by configuring a semVer like `2.0.*` or to minors and patches with `2.*.*`. In that
case, upgrading beyond patch or minor requires manual intervention and a commit in the gitOps repository. Tags
of this form should be created only from the `main` branch. That way a stable release is still created by a
developer by creating the `main#release#[patch,minor,major]` tag.

### "testing" stage

This one will deploy apps released with `2.0.0-rc.X` tags. We're assuming any tag matching the `-rc*` is
deployed automatically. If there are multiple developers working on the same app in parallel, they should
coordinate the `rc` release and figure out what they want to be deployed in the `testing` stage. `rc` tags are
not automatically generated, so the developers still have to create them explicitly. Tags of this form should
be created from the `main` branch. A release is created by a developer by creating the
`main#release#[patch-rc,minor-rc,major-rc]` tag.

### "dev" stage

We assume that the tags created on the dev branches have the format `[X.Y.Z]-dev.[branch_name].[date].[time]`.

In general case, an application deployment for "dev" environments should be configured to accept any tag
matching a dev build from a wanted tag, for example `*-dev.my-feature.*.*`. Applying this configuration is up
to the developer, depending on the usage scenario.

#### Working with "dev" stage on testing MCs

Most of the apps we work on get deployed on MCs and are tested during the development process on `testing`
channel MCs. Since running a whole MC with all its apps configured to run on dev builds would result in a
highly unstable and potentially unusable environment, we assume the apps running on such MCs will be
configured to auto-upgrade on stabel and RC releases only. When a developer wants to test a new dev branch of
an app, he will configure the app on one of the `testing` MCs to accept dev builds from the branch he/she
works on. This is an extension of the process we have in our `resrvations` channel in slack. So, the process
goes like this:

1. Announce on slack on `#reservations` that the `testing` MC named `M` is being reserved for testing the dev
   version of app `A` using the dev branch `new-feature`.
1. In GitOps repos, find the deployment manifest of the app `A` and change the accepted range of semVer from
   `*-rc\.*` to `*-dev\.new-feature\.*`.
1. Work on the new feature. Each commit to the branch `new-feature` results in a build and automatic
   deployment to the configured MC `M`.
1. When done, revert the commit from 2. in the GitOps repos and announce in `#resrvations` that the work there
   is done.

Because this is a multi-step process in which it's easy to forget about reverting the changes, we will add a
tool in `devctl` to automate it and automatically revert the dev deployment after a configured time. The
developer will name the MC, app, branch and time he wants to run the dev deployment for and the tool will
handle the process. If needed, it can obviously be still run manually.

### Emergency rollback

At some point, some releases will obviously fail. It is important that the developers know how to rollback the
configuration to the last known working state, if the "fix and roll forward" approach can't be used. There are
a few options possible:

1. For the affected resource, edit it ad hoc and change the versions that accepts a range to a specific known
   version or limit its range so that the failed version is not included. For gitops controlled resources,
   this has to be done in the gitops repo.
1. If the operator can't immediately change the config in the gitops repository, and the object is deployed
   from one, you can pause the reconciliation of the owning `Kustomization` object and then manually force a
   specific version of the app to be deployed.
1. If the object is not externally managed, just edit the version spec of the deployment object.

**Note**: Please remember that we can still reflect every version change of an object in the gitops repository
and then use the "rollback commit" solution, if we use the
[image automation controller](https://github.com/giantswarm/image-automation-controller) for setting the chart
version. This solution, however, requires constant manual approvals by a user and is not covered by this RFC.
