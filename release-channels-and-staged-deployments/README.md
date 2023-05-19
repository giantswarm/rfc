# Release channels and staged deployments

The document talks about releases, deployments, how we deploy components in different ways, when we deploy them.

It starts with an overview of what we have today, and then continues with how we can structure releases an deployments in the future.

## 1. What and when we release and deploy today?

### 1.1. What are we deploying?

1. cluster-x app
  - Cluster resources
  - Most critical apps: CPI, CNI, CSI
  - Owners: LM, CI, OPI

2. default-apps-x
  - Workload cluster apps
  - Owners: LM, CI, OPI

3. x-app-collection 
  - Management cluster apps
  - Owners: LM, CI, OPI

This means we can say that we have a have:
- Workload cluster 
- Management cluster version

Config is not included above. Applying, changing some config is usage of released APIs, it is not an act of releasing nor deploying. An app that is released exposes available config - setting and changing that config does not affect the release.

Components:
- Kubernetes
- Flatcar OS
- Upstream apps we package
- In-house apps we build
- Configuration of all the above (does not really goes into releases story)

### 1.2. When and how often are we deploying?

Today we and our customers have a need and use cases for deploying components in two different ways (when it comes to when and how often):
1. Automated continuous deployments
    - We use this approach mostly for MCs.
    - No need to go through a bigger release process.
    - Faster feedback loop when working on MC components, which can be especially important in KaaS Area.
    - Less control over upgrades, bugs can get deployed to many (all) clusters before catching them.
2. Manually triggered deployments
    - We use this approach mostly for WCs.
    - We use this approach for updating vintage WCs to newer releases.
    - This way we and the customers have more control over the cluster upgrades.
    - The control over upgrades can be especially important for some customers' production clusters where we also have freeze periods where we must not do updates.
    - It can be a problem when security and critical bug fixes have to be rolled out as soon as possible.

#### 1.2.1. Automated continuous deployments

Giant Swarm today in vintage:
- We continuously push some apps to app collections and those are being then deployed automatically to all MCs. (MC)

Giant Swarm today in CAPI:
- We continuously push some apps to app collections and those are being then deployed automatically to all MCs. (MC)
- We continuously deploy some of cluster-x apps to some management clusters with renovate automatically merging PRs. (WC, MC)
- We continuously deploy some of default-apps-x apps to some management clusters with renovate automatically merging PRs. (WC, MC)

#### 1.2.2. Manual deployments

Today in vintage:
- We and our customers manually update vintage WCs to newer releases.

Giant Swarm today in CAPI:
- We and our customers manually update clusters to newer cluster-x versions.
- We and our customers manually update clusters to newer default-apps-x versions.


## 2. Next step: release channels and staged deployments

This sections describes the new way for defining releases and deploying components. Most of the existing concepts and processes are kept, and then they are expanded and placed into new concepts.

The first new concept that we define here is release channels. Release channels differ in stability levels and release cycle frequency. All components are available in all release channels.

The second new concept that we define here are staged deployments. All components are delivered to all release channels in stages. We also define how we promote component versions (and other cluster changes) from one release channel to another.

From the above, we can say that the staged deployments consist of gradually promoting changes from one release channel to another with stability and release cycle frequency in mind.

Now let's go deeper.


### 2.1. Release channels

For release channels we define 3 stability levels, each of which has one or more release channels:
- Testing
- Staging
- Production

For production stability level we define 3 release channels, which have different release cycles, but all are considered to be production:
- Production Edge - fast rolling releases
- Production Current - normal point releases
- Production LTS - slow point releases

With all the above combined, we get a total of 5 release channels, where every cluster, both MCs and WCs, is configured to use one of:
- Testing
- Staging
- Production Edge - fast rolling releases
- Production Current - normal point releases
- Production LTS - (later future) slow point releases

All management clusters, using any release channel, can deploy workload clusters that are using any release channel.

Few notes, to give you an idea before going into details:
- When a component version is available in a release channel, it is automatically deployed to all clusters that are using that release channel. Deployments can be delayed for a limited time (e.g. customer freeze week) and a mechanism for that will be described later in this document.
- All component versions start from Testing, more stable ones go into Staging and the stable ones end up in Production Edge. Some of the stable component versions at some point become available in Production Current and Production LTS.
- Promotions from Testing to Staging and finally to Production Edge are time-based today (e.g. after X days) and can be accelerated manually. We will introduce quality-based promotions in the future.
- Production Current release channel gets new versions periodically. It has a well defined and predictable release cycle. It resembles point releases. Patches and fixes are deployed more often than features.
- Production LTS release channel gets new versions periodically, but less frequently than Production Current. It has a well defined and predictable release cycle. It resembles point releases. Patches and fixes are deployed more often than features.

Now to dive into more details.

#### 2.1.1. Testing

Release cycle description:
- **Automated continuous** delivery of beta, RC and GA/stable releases, depending on the component.
- **Automated continuous** delivery of all minor and patch releases. Component version can be defined as `1.*.*` (or simply `1.*`), where `1` is a fixed major version that will not change.
- Optional **Automated continuous** delivery of major component releases, where component version is defined as `*.*.*` (or simply `*`). Every team, decides for its components if major releases will have automated continuous delivery, based on their familiarity with stability and risk factors.

**Kubernetes releases**

Upstream releases with the following stability levels are included:
- Beta releases, optional, owning team can decide.
- Release candidates (RC)
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of beta, RC and GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Kubernetes version is defined as `1.*.*` (or simply `1.*`).

**Flatcar releases**

Upstream release channels that are used:
- Stable

Release cycle description:
- **Automated continuous** delivery of Flatcar releases from stable channel.
- Flatcar version is defined as `*.*.*` (or simply `*`).

**Cluster API releases**

Upstream releases with the following stability levels are included:
- Beta releases, optional, owning team can decide.
- Release candidates (RC)
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of beta, RC and GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Cluster API version is defined as `1.*.*` (or simply `1.*`).

**Releases of other upstream apps**

Release cycle and included stability levels for upstream apps that we are packaging and deploying to our clusters are aligned as much as possible with the release cycle description for Testing release channel (see the first paragraph in "2.1.1. Testing").

**Releases of Giant Swarm in-house built apps**

Release cycle and included stability levels for all Giant Swarm in-house built apps is fully aligned with the release cycle description for Testing release channel (see the first paragraph in "2.1.1. Testing").

#### 2.1.2. Staging

Release cycle description:
- **Automated continuous** delivery of RC and GA/stable releases, depending on the component.
- **Automated continuous** delivery of all minor and patch releases. Component version can be defined as `1.*.*` (or simply `1.*`), where `1` is a fixed major version that will not change.
- Optional **Automated continuous** delivery of major component releases, where component version is defined as `*.*.*` (or simply `*`). Every team, decides for its components if major releases will have automated continuous delivery, based on their familiarity with stability and risk factors.

Release promotion rules (unless defined differently for a specific component):
- Patch: Must be at least 1 working day in Testing before being promoted to Staging.
- Minor: Must be at least 3 working days in Testing before being promoted to Staging.
- Major: Must be at least 5 working days in Testing before being promoted to Staging.

**Kubernetes releases**

Upstream releases with the following stability levels are included:
- Release candidates (RC)
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of RC and GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Kubernetes version is defined as `1.*.*` (or simply `1.*`).

The only difference when compared to Testing is that the beta releases are not included.

**Flatcar releases**

Same as Testing.

**Cluster API releases**

Upstream releases with the following stability levels are included:
- Release candidates (RC)
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of RC and GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Cluster API version is defined as `1.*.*` (or simply `1.*`).

The only difference when compared to Testing is that the beta releases are not included.

**Releases of other upstream apps**

Release cycle, included stability levels and promotion rules for upstream apps that we are packaging and deploying to our clusters are aligned as much as possible with the release cycle description for Staging release channel (see the first two paragraphs in "2.1.2. Staging").

**Releases of Giant Swarm in-house built apps**

Release cycle, included stability levels and promotion rules for all Giant Swarm in-house built apps is fully aligned with the release cycle description for Staging release channel (see the first two paragraphs in "2.1.2. Staging").

#### 2.1.3. Production Edge

Release cycle description:
- **Automated continuous** delivery of GA/stable releases.
- **Automated continuous** delivery of all minor and patch releases. Component version can be defined as `1.*.*` (or simply `1.*`), where `1` is a fixed major version that will not change.
- Optional **Automated continuous** delivery of major component releases, where component version is defined as `*.*.*` (or simply `*`). Every team, decides for its components if major releases will have automated continuous delivery, based on their familiarity with stability and risk factors.

Release promotion rules (unless defined differently for a specific component):
- Patch: Must be at least 1 working day in Staging before being promoted to Production Edge.
- Minor: Must be at least 3 working days in Staging before being promoted to Production Edge.
- Major: Must be at least 5 working days in Staging before being promoted to Production Edge.

**Kubernetes releases**

Upstream releases with the following stability levels are included:
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Kubernetes version is defined as `1.*.*` (or simply `1.*`).

The only difference when compared to Staging is that the RC releases are not included.

**Flatcar releases**

Same as Staging.

**Cluster API releases**

Upstream releases with the following stability levels are included:
- General Availability (GA)

Release cycle description:
- **Automated continuous** delivery of GA releases.
- **Automated continuous** delivery of all minor and patch releases.
- Cluster API version is defined as `1.*.*` (or simply `1.*`).

The only difference when compared to Staging is that the beta releases are not included.

**Releases of other upstream apps**

Release cycle, included stability levels and promotion rules for upstream apps that we are packaging and deploying to our clusters are aligned as much as possible with the release cycle description for Production Edge release channel (see the first two paragraphs in "2.1.3. Production Edge").

**Releases of Giant Swarm in-house built apps**

Release cycle, included stability levels and promotion rules for all Giant Swarm in-house built apps is fully aligned with the release cycle description for Production Edge release channel (see the first two paragraphs in "2.1.3. Production Edge").

#### 2.1.4. Production Current

Production Current release channel has a well defined and predictable release cycle aligned with Kubernetes releases, meaning "bigger changes" of all components happen once in 4 months. This means that not all component versions will be available in this release channel, or at least not immediately. Patch releases, bug fixes, critical and security fixes are delivered more often.

Release cycle description:
- **Manual delivery** of hand-picked major and minor component releases. It happens every 4 months, aligned with Kubernetes release cycle.
- **Automated continuous** delivery of all patch releases.
- Component version can be defined as `1.1.*`, where `1.1` are fixed major and minor versions that will not change until the next release cycle.

Release promotion rules (unless defined differently for a specific component):
- Patch: Must be at least 1 working day in Production Edge before being selected for Production Current.
- Minor: Must be at least 3 working days in Production Edge before being selected for Production Current.
- Major: Must be at least 5 working days in Production Edge before being selected for Production Current.

**Kubernetes releases**

Upstream releases with the following stability levels are included:
- General Availability (GA)

Release cycle description:
- **Automated continuous** of all minor releases. It happens every 4 months (per upstream release cycle).
- Kubernetes version is defined as `1.27.*` (or simply `1.27`).

**Flatcar releases**

Upstream release channels that are used:
- Stable

Release cycle description:
- **Manual delivery** delivery of the latest major and minor Flatcar releases from stable channel.
- **Automated continuous** delivery of Flatcar patch releases from stable channel.
- Flatcar version is defined as `3510.2.*`.

The suggested release cycle requires further investigation into if it is possible to align such delivery of Flatcar releases with Kubernetes releases, and stay on supported Flatcar releases (i.e. not get into a situation where the Flatcar releases currently in use are not supported anymore).

Alternative release cycle (possibly not connected to Kubernetes release cycle) which would keep Flatcar more up-to-date can be:
- **Manual delivery** delivery of the latest major Flatcar releases from stable channel.
- **Automated continuous** delivery of Flatcar minor and patch releases from stable channel.
- Flatcar version is defined as `3510.*.*`.

**Cluster API releases**

TBA

**Releases of other upstream apps**

TBA

**Releases of Giant Swarm in-house built apps**

TBA

#### 2.1.5. Production LTS

Production LTS release channel will be added in the future. It will have a well defined and predictable release cycle that will rely on the (future) Kubernetes LTS releases. "Bigger changes" of all components happen once in 12 months. This means that not component versions in this release channel are the slowest to update. Patch releases, bug fixes, critical and security fixes are delivered more often.

In case we want to have it before official Kubernetes LTS, we align it with the current longer Kubernetes support, which is 12 months, but the upgrades will be challenging because we would do 3 Kubernetes version upgrades every time in order to get to the version that will be supported for the next 12 months.

Release cycle description:
- **Manual delivery** of hand-picked major and minor component releases. It happens every 12 months, aligned with Kubernetes LTS release cycle.
- **Automated continuous** delivery of all patch releases within the LTS release.
- Component version can be defined as `1.1.*`, where `1.1` are fixed major and minor versions that will not change until the next release cycle.

The above release cycle is a rough idea. More investigation is required in order to define it more precisely. Coming up with a well-defined long release cycle, where the components will not be often outdated (or worse, affected by critical bugs and security issues), will be a challenging task.

**Kubernetes releases**

Aligned with and/or relying on the future Kubernetes LTS releases.

**Flatcar releases**

Upstream release channels that are used:
- LTS

**Cluster API releases**

TBA

**Releases of other upstream apps**

TBA

**Releases of Giant Swarm in-house built apps**

TBA

### 2.2. Component-specific details

#### 2.2.1. Cluster API

When a new version of Cluster API is available in a release channel, most of management clusters across all providers get automatically upgraded.

Upgrades of some management clusters might be delayed if there are compatibility issues between Cluster API and provider-specific Cluster API implementation. In this case the upgrade is delayed until there is a new version of provider-specific implementation that is compatible with newer Cluster API release.

In case when provider-specific implementation lags behind for a longer period, it is the responsibility of the specific Cloud/Onprem Integration team to advocate and push for new releases in the upstream community. If technically possible, Cloud/Onprem Integration team can create a custom release of provider-specific (CAPx) controller by updating Cluster API version in the Giant Swarm CAPx fork.

In case when provider-specific implementation lags behind for a longer period to the point where used Cluster API version is not supported anymore by the upstream community, it is the responsibility of the Lifecycle Management team (owners of Cluster API) to backport as much security and critical fixes as possible to older Cluster API releases (which is done in Giant Swarm forks).

### 2.3. Development versions

Today, when working on a component, developers often deploy apps manually to the current test installations. This document does not talk about how the development process would look like.

A suggestion for a long term solution is to use local development environment and ephemeral MCs.

Short-mid-term solution during the transition period is to keep overriding component versions (same like today) in clusters that use one of the above defined release channels.

### 2.4. Implementation details

Many implementation details are out of scope of this document.

For example, when some app version should be automatically updated, that is done differently in x-app-collection and cluster-x/default-apps-x.

Also with the above definitions of release channels, same app that is a part of x-app-collection can have different versions in different release channels. This means that in app collections we have to implement support for an app having different versions per release channel, or each release channel having its own app collection (which can be implemented with multiple directories, git branches, etc).

App configuration is not explicitly mentioned anywhere, but it would be beneficial to roll out config changes in stages as well, starting from Testing, then going to Staging and Production.

## 3. Upgrade process for existing clusters

TBA
