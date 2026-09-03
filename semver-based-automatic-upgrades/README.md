---
creation_date: 2025-12-11
issues:
- https://github.com/giantswarm/giantswarm/issues/24237
- https://github.com/giantswarm/giantswarm/issues/37079
last_review_date: 2026-09-03
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: approved
summary: We want to use flux and flux-operator's automatic upgrades capabilities to create automatic upgrades for different release stages, so we don't have to manually or through extra automation care about those rollouts.
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
customers, who can use it with their own tagging schemes. However, the specific tag formats (`-b*t*c*`,
`-rc.*`, etc.) and the workflow described here are intended for Giant Swarm's internal release engineering
process. The main goal of applying this scheme is to achieve auto-upgrade capabilities for our MC apps and
cluster apps.

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

- "dev", deploy any version of an app that matches a dev build tag of one branch, like `*-b2069581735t*`
- "testing", deploy any version of an app that matches tag `*-rc.*`
- "stable", deploy any version of the app that matches tag `>=32.0.0` (this excludes `-*` tags, so
  pre-releases)

We can use this mechanism for any `HelmRelease` or `ResourceSet` object that is created on an MC, for any
object deployed to a local (MC) or a remote (WC) cluster. The proposed solution will result in "commit-less
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
set of deployed apps, where each app will define its own accepted semVer expression for tags.

To be able to use SemVer tags for this, we will need to enhance our CICD tooling to make the proposed git
tagging schema easier to use by the developers. The proposed schema is backward compatible for stable
releases, but adds and optional 'Release Candidate' stage and fixes the dev builds tagging, which right now is
not semVer compliant.

This RFC introduces two related parts. The second one, automated app upgrades, will become possible as a
configuration of a standard flux feature. It is blocked by implementing the first one.

### Tagging schema

In order to become semVer compatible and our tags to reflect software maturity, we will introduce the
following tagging schema:

- For the "stable" release, we keep the current tagging schema with tags matching `[0-9]+\.[0-9]+\.[0-9]+`
  (i.e. `1.9.1`)
- For the "release candidate" stage, we introduce a new tag according to the recommended way of semVer
  tagging: `rc` suffixed tags formatted `-rc.N` (i.e. `1.9.2-rc.1`)
- For `dev` builds, we want to build every commit of a non-`main` branch a developer is working on. The tag of
  such a build must identify the branch and the commit it comes from, and the tags must sort correctly
  according to semVer. The format is `[X.Y.Z]-b[CRC32_branch_name]t[YYYYMMDD][HHMMSS]c[commit_SHA]`. See
  [Dev build tags](#dev-build-tags) below.

#### Dev build tags

Because these tags are often used as Kubernetes attributes, they must be DNS- and label-compatible and at most
63 characters in total. The schema for these tags changed once. Both versions are documented here, because the
first one is already in use.

**The original schema (superseded).** The first approved schema appends the suffix
`-dev.[BRANCH].[YYYY-MM-DD].[HH-MM-SS].h[COMMIT_SHA]`, where `BRANCH` is the (sanitized) name of the branch
the build is coming from, the time stamp comes from the current commit's commiter date converted to UTC (so
the date displayed with `git log --format='%ci'` format, not the author's date) and `COMMIT_SHA` is the short
(7 hex chars) git hash of the built commit. Date and time use hyphens as separators (e.g. `2026-01-27` and
`09-49-59`) so that each part is a semVer alphanumeric pre-release identifier, which allows leading zeros and
maintains correct lexicographic sort order. The commit hash is prefixed with a literal `h` so the part is
always alphanumeric. To keep the tag inside the 63 character budget, the branch name is lowercased, sanitized
to `[a-z0-9-]` and, when the tag overflows the budget, shortened by dropping its middle and inserting a `--`
marker (e.g. `renovate-up--s-to-latest`). Example tag:
`1.9.2-dev.my-feature.2026-01-27.09-49-59.h1a2b3c4`.

**Why we change it.** The branch name is the only variable-length part of the tag, so the schema stays inside
the budget only by destroying the branch name, which is the part that makes the tag human-readable. Worse, the
63 character budget is not enough. Helm helper templates join the tag with the chart name and other strings,
so the final value overflows again and the chart truncates it a second time. The `.` and `-` characters inside
the tag can then become the last character of the value, which makes it an invalid Kubernetes label value.
This breaks real builds, see [issue #37079](https://github.com/giantswarm/giantswarm/issues/37079):

```text
konfigure-operator-1.2.2-dev.teams-alignment-branch.2026-07-02.
```

**The current schema.** Dev builds are tagged `[X.Y.Z]-b[CRC32_branch_name]t[YYYYMMDD][HHMMSS]c[commit_SHA]`.
If the last stable tag in history is `1.9.1` and the branch name is `my-feature`, the build results in a tag
like `1.9.2-b2069581735t20260127094959c1a2b3c4`. The parts are:

- `b[CRC32_branch_name]` is the CRC32 checksum of the full, unsanitized branch name, in decimal (at most 10
  digits). It pins a build to its branch with a fixed-width fingerprint, so no part of the tag needs
  truncation. The algorithm is CRC-32/ISO-HDLC, the variant that Go's `hash/crc32.ChecksumIEEE` and Python's
  `zlib.crc32` implement. Note that the POSIX `cksum` tool uses a different CRC-32 variant and returns a
  different value. `gitsemver` provides a command that prints the checksum for a branch name, and the build
  pipeline reports the checksum in the pull request. Example:

  ```sh
  $ printf '%s' my-feature | python3 -c 'import sys, zlib; print(zlib.crc32(sys.stdin.buffer.read()))'
  2069581735
  ```
- `t[YYYYMMDD][HHMMSS]` is the current commit's commiter date converted to UTC (the date displayed with
  `git log --format='%ci'` format, not the author's date), without separators.
- `c[commit_SHA]` is the short (7 hex chars) git hash of the built commit. The commit hash is the primary
  identifier of the deployed source; the time stamp is a convenience that lets a developer tell at a glance if
  the last build is deployed.
- The literal `b`, `t` and `c` prefixes separate the parts and make each of them alphanumeric. A pre-release
  identifier that is all digits is compared numerically and forbids leading zeros, which breaks time stamps.
- The schema drops the `dev.` prefix. The `-b` prefix already tells dev builds apart from `-rc.N` releases.

The result has these properties:

- The pre-release part has a fixed length of 35 characters (`-` + `b` + 10 + `t` + 14 + `c` + 7), so a full tag
  is about 40 to 45 characters. This leaves at least 18 characters for the strings that Helm templates add.
- The pre-release part contains no `.` and no `-`. A truncation of the tag therefore cannot end on an invalid
  character, unless the added strings are so long that the cut lands inside the `X.Y.Z` part.
- The pre-release part is a single alphanumeric identifier. For one branch the `b[CRC32]t` prefix is constant,
  so semVer compares the fixed-width time stamps. The chronological sort order per branch is correct.
- Two commits in the same second still produce two different tags, but the commit hash then decides their
  order, which is arbitrary.

### The default matching scheme for apps

This matching schema is proposed to achieve automatic upgrades functionality for different maturity levels of
our software. This is a generic solution, but we want to use for apps deployed to our MCs and for automatic
upgrades of WC clusters. Since this solution includes the usage of regexp, which tend to be error prone, we
will provide standard configuration templates users can use, so that no regexps need to be created from
scratch. It is important to note that the [semVer](https://semver.org/) implementation in flux is
[masterminds/semver](https://github.com/Masterminds/semver#checking-version-constraints), which is important
especially for versions comparisons.

- For `stable`, we use stable tags for all apps, so `*` semVer expression (in `OCIRepository`: `semver: "*"`,
  no `semverFilter`). If preferred, this can be limited by the app owner to be limit to a subset of stable
  releases, like `1.x.x` or `1.2.x`. In that case, upgrades beyond minor or patch version will require a
  reconfiguration of the match expression by the owner.
- For `stable-testing`, we use the newest stable or RC tag available for each app (in `OCIRepository`:
  `semver: "*-*"`, `semverFilter: ".*-rc\..*"`)
- For `testing`, we use by default the same tag matching as for `stable-testing`. App developers, that want to
  test a dev release of an app they are working on, will reconfigure the app's expression to match the dev
  builds of the branch they are working on. This will match the behaviour we have in the `reservations`
  channel. As an example, a dev working on a `my-feature` branch of app `X` will reconfigure, as part of the
  reservation process, the app's semver filter on the chosen `testing` MC from the default `.*-rc\..*` to
  `.*-b2069581735t.*` (in `OCIRepository`: `semver: "*-*"`, `semverFilter: ".*-b2069581735t.*"`), where
  `2069581735` is the CRC32 checksum of the branch name `my-feature`. The change will have to be reversed once
  the testing is done. As this is a multi-step process prone to human error, we will provide a tool to execute
  it in one go.

### Note on tag format flexibility

The RFC proposes `stable`, `rc`, and `dev` as the default solution we should use. Still, the naming of tags
and the configuration of accepted tags on app deployment won't be limited in any way and will allow app owners
to introduce new tag schemas and match expressions, if they need to do so. Owners can also configure the match
expression to match 1 tag exactly, effectively disabling any auto-upgrade on the app.

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
      build that will be tagged `X.Y.Z-bCRC32(NAME)tYYYYMMDDHHMMSScSHA`. Examples for a branch named
      `my-feature`, whose CRC32 checksum is `2069581735`:
      1. A new commit in a new branch `my-feature` + last commit in the parent tree is `1.2.3` =
         `1.2.4-b2069581735t20260112120959c1a2b3c4`
   1. If the branch name starts with the `nobuild/` prefix, builds are not automatically triggered, but a
      release can still be created by manually assigning a correct tag. This allows us to save resources on
      the build pipeline, OCI storage and release auto-upgrade processes.
      1. Example: there's a branch `nobuild/i-dont-care` and a developer creates a tag
         `1.2.3-b2069581735t20260112120959c1a2b3c4`: the build is triggered and pushed to the OCI registry.

### Note on promotion logic

The workflow described below can be also seen as a kind of version promotion workflow. Please note, that the
potential of implementing an automatic promotion is very limited and does apply only to promoting an app
through pre-release software maturity stages. Once the application is released and gets a stable tag, this
solution can't be easily used to move the same app version between different environments using stable app
releases. In that sense, the problem is outside of the scope of this RFC.

In other words, the process here focuses on automatically upgrading the software from a configured maturity
pipeline, but does not cope with promoting the same single version of an app across multiple environments.

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

We assume that the tags created on the dev branches have the format
`[X.Y.Z]-b[CRC32_branch_name]t[YYYYMMDD][HHMMSS]c[commit_SHA]`.

In general case, an application deployment for "dev" environments should be configured to accept any tag
matching a dev build from a wanted branch, for example `.*-b2069581735t.*` for the branch `my-feature`.
Applying this configuration is up to the developer, depending on the usage scenario.

#### Working with "dev" stage on testing MCs

Most of the apps we work on get deployed on MCs and are tested during the development process on `testing`
channel MCs. Since running a whole MC with all its apps configured to run on dev builds would result in a
highly unstable and potentially unusable environment, we assume the apps running on such MCs will be
configured to auto-upgrade on stable and RC releases only. When a developer wants to test a new dev branch of
an app, he will configure the app on one of the `testing` MCs to accept dev builds from the branch he/she
works on. This is an extension of the process we have in our `resrvations` channel in slack. So, the process
goes like this:

1. Announce on slack on `#reservations` that the `testing` MC named `M` is being reserved for testing the dev
   version of app `A` using the dev branch `new-feature`.
1. In GitOps repos, find the deployment manifest of the app `A` and change the accepted range of semVer from
   `.*-rc\..*` to `.*-b[CRC32 of new-feature]t.*`.
1. Work on the new feature. Each commit to the branch `new-feature` results in a build and automatic
   deployment to the configured MC `M`.
1. When done, revert the commit from 2. in the GitOps repos and announce in `#reservations` that the work
   there is done.

Because this is a multi-step process in which it's easy to forget about reverting the changes, we will add a
tool in `devctl` to automate it and automatically revert the dev deployment after a configured time. The
developer will name the MC, app, branch and time he wants to run the dev deployment for and the tool will
handle the process. If needed, it can obviously be still run manually.

### Emergency rollback

At some point, some releases will obviously fail. It is important that the developers know how to rollback the
configuration to the last known working state, if the "fix and roll forward" approach can't be used. There are
a few options possible:

1. For the affected resource, edit it ad-hoc and change the versions that accepts a range to a specific known
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

## Decisions

### 2026-07-06 Dev build tags use `[X.Y.Z]-b[CRC32_branch_name]t[YYYYMMDD][HHMMSS]c[commit_SHA]`

The original dev tag schema `[X.Y.Z]-dev.[branch_name].[YYYY-MM-DD].[HH-MM-SS].h[commit_sha]` embeds the
branch name, which is variable in length. Tags therefore need truncation, and the truncated result can still
overflow the 63 character limit after Helm templates join it with the chart name. The second truncation can
cut the value at a `.` or a `-`, which makes it an invalid Kubernetes label value and breaks the deployment.

We replace the branch name with the CRC32 checksum of the branch name and remove all separators from the
pre-release part. This makes the pre-release part fixed-width (35 characters) and free of `.` and `-`. We keep
a human-readable time stamp instead of an epoch time stamp, because it costs 4 characters and lets a developer
tell at a glance whether the last build is deployed. We keep the commit hash, because it stays the primary
identifier of the deployed source. We drop the `dev.` prefix, because the `-b` prefix already tells dev builds
apart from `-rc.N` releases.
