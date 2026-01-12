---
creation_date: 2025-12-11
issues:
   - https://github.com/giantswarm/giantswarm/issues/24237
last_review_date: 2025-12-11
owners:
   - https://github.com/orgs/giantswarm/teams/team-honeybadger
status: review
summary: We want to use flux and flux-operator's automatic upgrades capabilities to create automatic upgrades for different release stages, so we don't have to manually or through extra automation care about those rollouts.
---

# Using semVer tags for automatic app upgrades in different release stages

## Introduction

Flux can automatically detect and apply new releases of a Helm Chart as new tags for the configured chart are created in
the OCI repository. These upgrades can be based on matching the semVer tag as both a semVer range and a regexp to match. We can use
[semVer tags, tag ranges and regexp filters](https://fluxcd.io/flux/components/source/ocirepositories/#reference) to
decide which tags will be considered for the automatic upgrade and which won't.

Using the feature and combining this with a defined tagging schema will allow us to create a process, where a developer
drives automatic upgrades for specific release stages by just assigning git tags of specific format to Helm Chart
releases. No configuration with the deployment tools will be required.

For example, if we want an app to be automatically deployed and patched as soon as a new patch release is available
(let's assume this is a valid behavior for a stable stage), we can configure the automatic upgrade semVer for the app to the `X.Y.*`, where "X" and "Y" are set to
specific values, and the `*` means that any patch release will be automatically deployed. That way we can automatically deliver fixes for an app (including security) without manually configuring the cluster to select and app version to run.

Now, if we want to expand this idea to multi-stage deployments, we can configure different stages with different semVer
expressions. For example:

- "dev", deploy any version of an app that matches tag `*-dev.*`
- "testing", deploy any version of an app that matches tag `*-rc.*`
- "stable-32", deploy any version of the app that matches tag `>=32.0.0` (this excludes `-*` tags, so pre-releases)

We can use this mechanism for any `HelmRelease` or `ResourceSet` object that is created on an MC, for any object
deployed to a local (MC) or a remote (WC) cluster. The proposed solution will result in "commitless gitops workflow", where
the version of an app to deploy is deterministic, but is calculated dynamically based on the semVer expression stored in
the deployment object (possibly in a gitops repo) and from the set of tags discovered in an OCI registry. The specific version of a chart to deploy will be calculated dynamically and will not be stored in the gitops repo.

Please note that this RFC proposes the format and semantics of different tags, but doesn't strictly define how to assign different selection rules to different stages. The problem of creating and configuring such changes will be solved separately and was described in [this RFC](../release-stages-collection/README.md) for collections. It will be enhanced to other apps as well.

*Note*:
In case we want to have a manual approval process for rolling any version change for an app, we can still configure
`ImageAutomationController` to push to a separate branch, and then we can review and merge it manually.

## Use cases

- We want to have our app releases automatically applied to different MCs, so that we can test them over longer runs. We
  want to group our MCs into stages, where we automatically upgrade first testing, then our stable MCs, only then
  customers (just an example).
- We want automatic rollouts, so that a new release of app is applied automatically, without further manual
  configuration, but only to selected MCs.
- This also includes any apps deployed to WCs, as long as they are defined on an MC. This means that we can use this with our customers to let them test pre-releases of the giant swarm maintained software.
- This covers also time-restricted/scheduled upgrades, if they come from `flux-operator`.

## Out of scope use cases

The following are right now considered out of scope of the current work, but still valid for the future:

- promotion tools: allowing a change (accepted tags configuration) to be propagated from 1 release channel to another in
  an automated way
  - use case: upgrading customer's WCs by release channel, gated and accepted by a user

## Implementation Idea

### Overview

We will introduce strict opinionated tagging patterns, then will assign acceptable tag ranges and regexp matchers to clusters of
specific release stage.

### Implementation idea

We will use `flux-operator` and `helm-controller` abilities to discover tags in remote OCI repositories using the new
recommended `OCIRepository` object. Tags matching the configured semVer expression will be applied to related
`ResourceSets` or `HelmReleases`. Each release channel will provide tag acceptance criteria for the set of deployed apps (mostly `collections`),
where each app will define its own accepted semVer expression for tags.

To be able to use SemVer tags for this, we will need to enhance our CICD tooling to make the proposed git tagging schema
easier to use by the developers.

Proposed tagging schema and its tentative mapping to MC stages:

- Deployments for Giant Swarm `dev` MCs should install the most recent dev release available. So, for the "dev" base, we
  deploy apps with `dev` tags matching "[0-9]+\.[0-9]+\.[0-9]+-dev\.(branch)\.[0-9]+" (ie. `1.9.2-dev.my-feature.1`)
  - **Note**: alternatively, we can set it to "*-*" to install any latest version, including pre-releases. Please note that "*" matches stable releases only, so no pre-releases are considered to match, unless you explicitely set the pattern to accept them.
- We want a separate set of rules to apply for giant swarm testing MCs. So, for the "testing" base we deploy apps with
  `rc` tags matching "[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+" (ie. `1.9.2-rc.1`)
  - If we want to make it more granular and for example include a separate stage for giant swarm "testing",
    "stable-testing" and customer stage "testing", we can use different pre-release prefixes, like: `alpha` - giant
    swarm testing, `beta` - giant swarm "stable testing", `rc` - customer testing
- For the "stable" stage, we deploy apps with tags matching "[0-9]+\.[0-9]+\.[0-9]+" (ie. `1.9.1`)

The above means that the deployed version of an application will entirely depend on the set of semVer tags available in
a remote OCI registries. In other words, developers decide where a specific version of an app will be deployed by
assigning tags to releases they create.

Since a release stage has completely independent set of app configurations, including the set of configured semVer
expressions, we can do anything that is possible by tag manipulation. As an example, in one release stage we can disable
autoupgrade capabilities entirely by pinning app versions to static semVer tag, like `1.1.1`.

### Implementation steps

1. We agree on the currently configured set of release stages.
1. We agree on the supported set of tag formats for each stage.
1. We implement changes in our CICD process, so the tagging schema is easy to follow.
1. We set the accepted semVer ranges for the apps in each stage. To avoid manually setting ranges for each existing app,
   we can use the patching feature of `Kustomizations` and - for example - patch the version of every deployed HelmRelease to the correct default value for this stage, ie. a testing cluster deployment sets and app version to `*-rc.*` by default.

### CICD process changes

1. We keep the current `main#release#[patch,minor,major]` logic, that will now create tags that are considered stable releases.
1. We add new `main#release#[patch-rc,minor-rc,major-rc]` logic, that will bump the selected part of the tag, but create a RC tag for it. Examples:
   1. `1.2.3` + `main#release#patch-rc` = `1.2.4-rc.1`
   1. `1.2.3` + `main#release#minor-rc` = `1.3.0-rc.1`
   1. `1.2.3` + `main#release#major-rc` = `2.0.0-rc.1`
   1. `1.2.3-rc.1` + `main#release#patch-rc` = `1.2.4-rc.2`
1. We don't build any commit from any branch by tagging it with `X.Y.Z-commit_hash`. The tags of this form are not semVer compatible and will result in incorrect sorting of tags.
1. The above will be replaced with the following automation:
   1. If there's a branch named `devrelease/[NAME]`, then every commit in this branch will trigger a build that will be tagged `X.Y.X-dev.NAME.Z`. Examples for a branch named `devrelease/my-feature`:
      1. first commit in a new branch `devrelease/my-feature` + last commit in the parent tree is `1.2.3` = `1.2.3-dev.my-feature.1`
      1. 10th commit in the same branch `devrelease/my-feature` + last commit in the parent tree is `1.2.3` = `1.2.3-dev.my-feature.10`
   1. If the branch name doesn't have the `devrelease` prefix, builds are not autoamtically triggered, but a release can still be created by manually assigning a correct tag.
      1. Example: there's a branch `i-dont-care` and a developer creates a tag `1.2.3-dev.awesome.1`: the build is triggered and pushed to the registry.

## Example developer's workflows and the related release process

Let's assume we have 3 release stages: dev, testing and prod. Each of them is assigned to a group of clusters and configures a
separate set of semVers for apps.

### "stable" stage

Each app in this release stage is configured to deploy only stable releases, with tags matching `X.Y.Z`, like `2.0.0`. Each time
a new stable release of any of the apps is created on GitHub, the build succeeds and a new chart is uploaded to the OCI
registry, the app will be automatically deployed to matching clusters. We can limit this to patch releases by
configuring a semVer like `2.0.*` or to minors and patches with `2.*.*`. In that case, upgrading beyond patch or minor
requires manual intervention and a commit in the gitOps repository. Tags of this form should be created from the `main`
branch. That way a stable release is still created by a developer by creating the `main#release#[patch,minor,major]` tag.

### "testing" stage

This one will deploy apps released with `2.0.0-rc.X` tags. We're assuming any tag matching the `-rc*` is deployed
automatically. If there are multiple developers working on the same app in parallel, they should coordinate the `rc`
release and figure out what they want to be deployed in the `testing` stage. `rc` tags are not automatically generated,
so the developers still have to create them explicitly. Tags of this form should be created from the `main` branch. A release
is created by a developer by creating the `main#release#[patch-rc,minor-rc,major-rc]` tag.

### "dev" stage

On selected "dev" MCs, we configure automated upgrades to always deploy the latest discovered tag matching a dev
release. This means that by default a "dev" cluster always runs the latest build from _any dev branch_ that decided to
create a tag matching the dev build. We assume that the tags created on the dev branches have the format
`[X.Y.Z]-dev.[branch_name].[build_number]`. By default, we configure dev stage apps to accept any tag having the `-dev`
suffix, accepting any branch name. This can be limited by a developer working on the app.

From a developer's perspective, he/she should choose whether to deploy to the "dev" stage or not. If yes, we want to
create an automation that makes it easier for the developers. The idea is that he/she has to work on a branch that
matches a naming schema, like `devrelease/my-branch`. The CI/CD process will be adjusted so that every commit on this
branch results automatically in a build and tag that matches `X.Y.Z-dev.my-branch.W`, where `W` is the number of
commits since the fork. Of course, such tags can be also created manually, from a branch with any name.

Since for "dev" environments the latest tag is discovered and applied automatically, the new dev version will be
deployed and available for testing as soon as the CI/CD pipeline finishes. There's nothing the developer has to do
except naming the branch.

This solution can create a problem when we have parallel builds for different features, like when multiple developers
work in parallel on different features of the same app, on different branches. In this scenario, each developer creates
a series of tags based on its own branch name (automatically for each commit or manually). Let's assume one developer
works on `app-operator` app in a branch `lukasz-feature`. Each of his builds should generate a tag formatted like
`2.0.0-dev.lukasz-feature.1`. Now, he might want to "lock a dev cluster" to this single branch builds, so no builds
from other dev branches are deployed there. He needs to go to the GitOps repo and reconfigure automatic deployments
regexp (for 1 cluster where you want to test your builds) into `2.0.0-dev\.lukasz-feature\.\d+`. This should "lock"
your cluster for testing only this branch (more specifically, releases tagged from that branch). Your "lock" commit in
the GitOps repo should also have pretty clear comment, like "Fixing dev version of app-operator to deploy from
'lukasz-feature' branch on 'golem'". Please note, that `lukasz-feature` based builds will be still deployed to any other
"dev" MC, according to the "deploy any latest dev build" default config. If your colleague wants to test his changes on
another MC, without you constantly overwriting deployments of his builds, he has two main options. One is to share a dev
branch with you, so you constantly integrate your work and automatically deploy every build. The other is that he
"locks" other dev "MC" for his own independent testing.

In any case, when your lock (or locks) are no longer needed, you have to revert the locking commit int GitOps repo.

### Full development workflow example

In this example, we simulate a developer working on a new feature of the `hello-world` app, assuming we have the 3
release stages mentioned above. The last stable release of the app is `1.2.2`.

1. The developer creates a new branch called `devrelease/new-feature` and starts working on the code. Since the branch
   has the `dev-deploy` prefix, every commit to this branch results in a build that is tagged
   `1.2.3-dev.new-feature.X`. Because this tag is "accepted" by `dev` stage apps, every build is automatically deployed
   to dev MCs.
1. When the developer is happy enough with the new feature, he/she merges the `dev-deploy/new-feature` into `main`,
   solves potential problems and creates a new `rc.1` tag. When built, this app version is automatically deployed to
   clusters with the `testing` semVer configured.
1. After testing for some time and fixing potential problems, the developer is ready to release a stable version. He
   does that by bumping the `minor` component of the version tag, marking this release as API backward compatible, but
   providing new features. The new version is picked up automatically by flux running on "stable" clusters.

### Emergency rollback

At some point, some releases will obviously fail. It is important that the developers know how to rollback the configuration to the last known working state, if the "fix and roll forward" approach can't be used. There are a few options possible:

1. For the affected resource, edit it ad hoc and change the versions that accepts a range to a specific known version or limit its range so that the failed version is not included. For gitops controlled resources, this has to be done in the gitops repo, possibly taking into account patches that default the app version.
1. If can't immediately change the config in the gitops repository, and the object is deployed from one, you can pause the reconciliation of the owning `Kustomization` object and then manually force a specfic version of the app to be deployed.

**Note**:
Please remember that we can still reflect every version change of an object in the gitops repository and then use the "rollback commit" solution, if we use the [image automation controller](https://github.com/giantswarm/image-automation-controller) for setting the chart version. This solution, however, requires constant manual approvals by a user and is not covered by this RFC.

## Necessary changes

1. We need to change our tagging and releasing CICD automation
1. We need to make sure that when a new chart is available in an OCI registry, the images it uses are also already
   available, otherwise the automatic chart update will fail because of the image.
