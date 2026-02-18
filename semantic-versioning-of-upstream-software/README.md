---
creation_date: 2025-11-27
issues:
- https://github.com/giantswarm/giantswarm/issues/33597
owners:
- https://github.com/orgs/giantswarm/teams/sig-architecture
state: review
summary: Describes our approach for versioning our own packages of upstream software.
---

# Semantic Versioning of Upstream Software

## Background

Giant Swarm is moving towards more extensive release automation as described in [RFC Semver Based Automatic Upgrades][6].
This automation relies on [SemVer][1] to determine ordering of release versions.
Most of Giant Swarm's apps were already compliant, but some added an incrementing suffix like `-gs1`.
These are apps that package upstream software that have versioning over which we have no control.
For example, upstream version `1.0.0` gets packaged as `1.0.0-gs1`.
We increment the suffix for every build of version `1.0.0` that we publish.
This allows us to create as many packages as we want while staying coupled to the upstream package version.
However, while these are parseable as a semantic version, `1.0.0-gs10` is lesser than `1.0.0-gs2`.
That is not intuitive, and is not compatible with the aforementioned RFC.

It was then requested of the teams to change their package versioning schemes to be strictly SemVer compliant.
After an internal discussion, Team Phoenix decided to decouple the package version from the upstream version.
For example, even though the upstream version might be `1.2.3`, our package version could be `2.0.0`.
Decoupling the versions would let us make breaking changes in our packaging whenever we like.
The tradeoff is that the deployed upstream version is less clear.

Team Phoenix did not really discuss their decision with the other teams.
Unfortunately, we found out that Team Tenet was building automation that relied on this very same coupling that Team Phoenix decided to remove.
This lead to confusion and frustration, with inconsistency between teams making it harder to build and maintain automation.
It was clear that a more considered and company-wide decision had to be made.

A meeting was then held in SIG Architecture with representatives of every engineering team, leading to this RFC.

## Problem Statement

The packaging of upstream apps MUST strictly follow the rules set by [RFC Semver Based Automatic Upgrades][6].
Deviation from the rules would break automatic upgrades.

## Proposed Solution

We will remove any coupling of versions between upstream software and our packages of said software.
To make it clear that formerly coupled packages are no longer so, we have released a new major version to make the removed coupling clear.

We always document the upstream version, for example in the `appVersion` field for Helm charts.

We strictly follow the rules set by [RFC Semver Based Automatic Upgrades][6].

## Considered Alternatives

### Different Suffixes

There are ways to have suffixed versions ordered correctly according to the SemVer spec.
However, any kind of different suffixing would be incompatible with [RFC Semver Based Automatic Upgrades][6].

### Build Metadata

SemVer supports adding [build metadata][5], but this is ignored during ordering.
Versions `1.2.3+foo` and `1.2.3+bar` are both considered equal by SemVer.
In this case, selection of the version becomes random.

### Consistent Coupling

The main point of this decision is to provide consistency across the engineering teams to build the automation on.
Consistently coupling all packages of upstream software to the upstream version could then be an option.
If our packaging must be changed without updating the upstream software, we could simply release a patch version of our package.
For example, package `1.1.1` could deploy upstream `1.1.0`.

However, there are two main problems with this approach:

1. Many apps are already decoupled, with packages released with versions greater than the upstream version.
   An app with upstream version `1.2.3` may already have a Giant Swarm release versioned `2.0.0`.
   If we then recouple the package and upstream version, at some point upstream can decide to release version `2.0.0`.
   Unless we "unrelease" our original `2.0.0` (that deployed upstream `1.2.3`), this would cause our release automation to deploy older software.
2. We would have no way of making a breaking change in our packaging until upstream releases a new major version.
   While it could be argued that we should not be making breaking changes until upstream does, we should not put ourselves in a position where we do not have the option of doing so.


[1]: https://semver.org/
[2]: https://semver.org/#spec-item-9
[3]: https://helm.sh/docs/helm/helm_install/#options
[4]: https://semver.org/#spec-item-11
[5]: https://semver.org/#spec-item-10
[6]: ../semver-based-automatic-upgrades/README.md
