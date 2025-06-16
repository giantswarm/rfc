---
creation_date: 2025-05-29
issues:
  - https://github.com/giantswarm/roadmap/issues/4001
last_review_date: 2025-05-29
owners:
  - https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary:
  This RFC presents a solution that will allow our customers and us to configure automated app upgrades,
  including cluster apps, according to a pre-defined policy, that includes time schedule and version
  restrictions.
---

# Automatic app upgrades

The goal is to be able to schedule automated app upgrades (Helm chart version upgrades) for deployments
present on Management Clusters. The proposed solution has to support cluster deployment apps.

## Assumptions and requirements

- has to work without GitOps, but must be able to integrate with it
- has to support schedules
- works on MC, but targets any resources (so including App CRs and HelmReleases targeting remote WCs)

## Problems

Won't work with the current cluster Release process, where chart version is not really the version deployed.

## Rough idea

We create a new operator (tentative name "version-upgrade-operator") and a set of CRDs which will provide and
act on information about where to discover the latest available version tags, when to update them and on which
resources.

The new CRs will allow to provide a reusable schedule object, version discovery source and covering many
target CRs with just 1 instance. The new CRs will be separate from the controller being actually responsible
for application deployment (like helm-controller or app-operator).

We design the version setting for App CRs and HelmReleases, but the solution is not CR specific. Using the new
CRDs, an operator will be responsible for setting target CRs' selected property, like the `spec.version` of
App CR, to an automatically determined value. The value will be discovered in a Helm charts repository and
applied to a target CR only when time-based restrictions are met.

### Image tags and registries discovery

For the solution to work, we have to discover tags available for specific image (repository) in a registry. We
figured out that instead of implementing our own logic for discovering tags, we can reuse the existing logic
present in Flux controllers.

#### Reusing Flux components

Flux has version discovery implemented in a few places:

- `HelmRelease/HelmRepository/HelmChart` level: these are the objects that drive actual Helm Chart deployment.
  We want to edit them to point to a limited set of possible versions to make them work with the operator
  we're designing
- `OCIRepository` which allows to discover and filter tags of artifacts in an OCI repository; it is always
  downloading the most recent matching artifact
- `ImageRepository` and `ImagePolicy` are objects normally used by
  [`ImageAutomationController`](https://fluxcd.io/flux/components/image/), but we can use them for easy
  discovery of what's available in a registry.

To not interfere with how upgrades might be already configured for existing `HelmReleases`, we will use a
dedicated `ImageRepository` and `ImagePolicy` objects for discovery process related to automatic upgrades.

##### How this would work?

To configure an automated update for an App CR, we need answers to 3 key questions: 1) what should be
upgraded; 2) when it should be upgraded; 3) which version should be used. The following steps have to be
performed by a user and the new operator (this assumes that there's no GitOps interfering, deployment with
GitOps is described below):

1. The user deploys an application, either by using `App CR` and a related `Catalog` or `HelmRelease` and
   `HelmRepository`
   - at this point, Flux or another related deployment operator are already performing Helm Chart deployment
1. The user has to define an automated version upgrade policy
   - if it doesn't exist or a user wants to own the object, he creates an `ImageRepository` object, that
     points to a specific repository (application, helm chart) of an OCI registry. `ImageRepository` discovers
     and knows all the tags in a remote repository of a registry. There's an exclude regexps list to skip
     stuff you're sure you won't ever need.
     - The relationship between `ImageRepository` and `HelmRepository` is very close, we can probably automate
       `ImageRepository` creation so that users don't have to manage them
   - The user now creates an `ImagePolicy` object, which determines the range of applicable versions, out of
     all found by `ImageRepository`. `ImagePolicy` is a filter for `ImageRepository`. You give it a SemVer
     range and it filters out everything and leaves only the newest tags matching your policy; it's a n:1
     relationship with `ImageRepository`, so `ImageRepositories` can be shared. The `ImagePolicy` object
     defines the "which version?" part of the controller's input parameters.
   - The user either creates or reuses `VersionUpgradeSchedule` object (see below). This part delivers the
     "when?" part of automatic upgrades configuration.
   - Then, the user creates a `VersionUpgradeConfig` object that is providing only the following information
     - which `ImagePolicy` to reference and use as a source of truth about available tags
     - which `VersionUpgradeSchedule` to reference and use as a source of information about when to update the
       target Resources
     - how to find target Resources and where to put the version info in them

### GitOps integration

To make it possible to use `VUO` for objects coming from a GitOps repo, the target object's version cannot be
kept in the GitOps repo anymore (in case it's used). Instead, the operators acting on the target CRs must
accept the fact that they don't manage the configured version property, and that the automatically discovered
version is placed there.

Even though this approach limits (only a bit) the disaster recovery properties of the GitOps approach, it is
important to note that for the specific set of `VUO` CRs, `target CR` and the set of discovered tags, the
calculated version is deterministic. We will also try to provide good reporting in the status field of `VUO`
CRs, including info about what was discovered and what was updated.

In case of GitOps deployments of App CRs, we have to change all the CRs so that Flux doesn't manage the
version field of the App CR and doesn't fight with `version-upgrade-operator` to set it. This might also need
some changes in `app-operator` and/or `app-admission-controller`.

With `HelmReleases`, the problem is that when no version is provided, it will default to `latest`. It means,
that when you add a new `HelmRelease` to your GitOps repo, without setting the version, the version will be
set to `latest` and then the app will be installed (if only the `latest` tag exists). To solve this issue,
`VUO` will by default inject a pre-configured application version in any newly discovered target object, even
if it's outside of an upgrade window, assuming the following conditions are met:

- there's no value in the target's version property or it is `latest`
- the upgrade CR has an optional `defaultVersion` field configured.

Still, the feature above might result in an app being first installed with the `latest` tag and only later
downgraded to the correct version resulting from its automated version upgrade policy. This might be a
problem, as not all apps correctly handle downgrades and may break in the process. If you need to avoid
installing (or attempting installation) of the `latest` version, you might need to first commit the target
object into repository with a flag like `suspend: True` and flip this flag only after the initial version is
set.

Please also note, that if you're a GitOps user, resolving directly to Flux's
[auto upgrade capabilities](https://fluxcd.io/flux/guides/image-update/) might be a better solution for you.

### Spec draft and example

For a `trivy` App, we want to update all instances of `App` CRs that have a specific label with the latest
`rc` release.

The relevant Flux objects used for version discovery (once again, might be changed by an equivalent solution):

#### Version discovery

```yaml
# potentially ImageRepository CR can be auto-generated
---
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: trivy
spec:
  image: myregistry/trivy
  interval: 1h
  provider: generic
status:
# ...
  lastScanResult:
    latestTags:
    - v1.4.2
    - v1.4.1
    - v1.4.0
    - v1.3.1
    - multiarch
    - master-t0dgwgrs
    - master-a9a1252
    - latest
    - ff1fb39
    - fed964e
    scanTime: "2025-04-28T13:01:59Z"
    tagCount: 227
---
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: trivy-rc
spec:
  imageRepositoryRef:
    name: trivy
  policy:
    semver:
      range: ">= 1.0.0"
    filterTags:
      pattern: ".*-rc.*"
status:
# ...
status:
  conditions:
  - lastTransitionTime: "2025-04-24T12:16:37Z"
    message: Latest image tag for 'registry/repo' updated from 0.4.11-rc.1 to 1.1.1-rc.1
    observedGeneration: 2
    reason: Succeeded
    status: "True"
    type: Ready
  latestImage: registry/repo:1.1.1-rc.1
  observedGeneration: 2
  observedPreviousImage: registry/repo:0.4.11-rc.1
```

#### Upgrade schedule definition

The new CRDs:

```yaml
# This object is container data only, so doesn't have any status fields
kind: VersionUpgradeSchedule
metadata:
  name: upgrade-stable-at-night
  namespace: org-testorg
spec:
  # valid (optional)
  #
  # Decides the time window when the reconciliation is in power.
  #
  # The CR gets reconciled at `.spec.interval` intervals, but upgrading is performed only in
  # any of the [spec.valid.from, spec.valid.to] time windows. Setting version changes on targets
  # outside of any these windows is suspended.
  # If multiple windows are used, they have to be disjoint. Does still run discovery even outside of "valid" windows.
  #
  # To suspend indefinitely use 'valid.from: "Inf"'
  valid:
    - from: "2025-05-05 05:05" # (optional, defaults to "now") start of the time frame when version changes to targets are allowed
      to: "2026-05-05 15:05" # (optional, defaults to +inf) end of the time frame when version changes to targets are allowed
      timezone: "Europe/Berlin" # (optional, defaults to UTC) timezone in which the time is expressed

  # upgradeWindows
  #
  # Defines all the possible upgrade windows. The windows are ORed together, so upgrade will be triggered for any
  # reconciliation that falls within any of the windows. Within a single window, the conditions are ANDed together,
  # so `dayOfWeek: Wed ` and time: 7:00` means "only on Wednesdays at 7:00".
  # There has to be at least 1 window on the list.
  upgradeWindows:
    # dayOfWeek: expressed as common short names. Can be a single day ('Mon'), a single range of days ('Mon-Fri'),
    # or a comma-separated list of days ('Mon,Wed,Fri'). "*" is an alias for "every day".
    #
    # dayOfMonth: number of a day within a month. Can be a single day ('1'), a range of days ('1-5'), or a comma-separated list of days ('1,3,5').
    #
    # time: time the window starts, in the format "HH:MM" (24-hour clock) (UTC if `timezone` not given).
    #
    # duration: how long is the upgrade window opening.
    #
    # timezone: (Optional) according to which TZ. It's UTC by default.
    - dayOfWeek: Mon
      time: "02:34"
      duration: 10m
    - dayOfMonth: "1,11,21"
      time: "02:34"
      duration: 60m
      timezone: "Europe/Berlin"

  # Here are possible combinations of values.
  #
  # 1. Don't apply any version changes before 2025.05.05 05:05.
  #    Then upgrade as normal at each reconciliation if necessary.
  #
  # spec:
  #   valid:
  #     - from: "2025.05.05T05:05Z"
  #
  # 2. Reconcile CR target only within the [04:00, 04:10)
  #    time window.
  #
  # spec:
  #   upgradeWindows:
  #     - dayOfWeek: '*'  # on all days
  #       time: "04:00" # at 4:00 UTC
  #       duration: 10m0s
  #
  # 3. Reconcile CR target only within the [04:00, 04:20)
  #    time window *and* after 2025.05.05 05:05.
  #
  # spec:
  #   valid:
  #     - from: "2025.05.05 05:05"
  #   upgradeWindows:
  #     - dayOfWeek: '*'  # on all days
  #       time: "04:00Z" # at 4:00 UTC
  #       duration: 20m # for 20 minutes
  #
  # 4. Reconcile CR target only within the "[04:00, 04:20) on the first Monday of a month"
  #    time window *and* after 2025.05.05 05:05 *and* before 2026.05.05 05:05.
  #
  # spec:
  #   valid:
  #     - from: "2025.05.05 05:05"
  #       to: "2026.05.05 05:05"
  #   upgradeWindows:
  #     - dayOfWeek: Mon
  #       dayOfMonth: 1-7  # there can be only 1 Monday between 1st and 7th of a month
  #       time: "04:00Z" # at 4:00 UTC
  #       duration: 20m # for 20 minutes
  #
  # 5. Reconcile CR target only within the "[04:00, 04:20)" window on each Monday
  #    but not during Christmas holidays, so between [2025.12.01 00:00, 2026.01.01 00:00].
  #
  # spec:
  #   valid:
  #     - to: "2025.12.01 00:00"
  #     - from: "2026.01.01 00:00"
  #   upgradeWindows:
  #     - dayOfWeek: Mon
  #       dayOfMonth: 1-7  # there can be only 1 Monday between 1st and 7th of a month
  #       time: "04:00Z" # at 4:00 UTC
  #       duration: 20m # for 20 minutes
```

#### Version upgrade configuration

```yaml
# namespace scoped Custom Resource
kind: VersionUpgradeConfig
metadata:
  name: trivy-auto-upgrade
  namespace: org-testorg
spec:
  # suspend
  #
  # Suspend the reconciliation of this resource.
  suspend: False

  # serviceAccountName
  #
  # Service Account name in the `.metadata.namespace` to perform upgrades with.
  #
  # The question is, even if we grant customers an admin access, do we still consider
  # them and us as separate tenants? If so, then we have kind of multi-tenancy, and since
  # it would be nice to implement it with the Kubernetes RBAC, we need a SA, the same way Flux
  # does it.
  #
  # If we do not care, we can allow the controller to always reconcile resources with its
  # default permissions, presumably the `cluster-admin`.
  serviceAccountName: "automation"

  # interval
  #
  # Reconciliation interval.
  interval: 5m

  # targets
  #
  # A list of targets to upgrade. They have to be in the same namespace. This can be either specific
  # targets listed by kind and name or wildcards using label selectors.
  # Name and labelSelector are mutually exclusive.
  #
  # Each target defines a path to its version holding property that should be updated.
  targets:
    - kind: App
      field: spec.version
      name: cluster3-trivy
    - kind: HelmRelease
      field: spec.chart.spec.version
      name: cluster1-trivy
    - kind: OCIRepository
      field: spec.ref.semver
      name: trivy
    - kind: HelmRelease
      field: spec.chart.spec.version
      labelSelector:
        app: trivy
        stage: production
        vucUpdate: true

  # versionSourceRef
  #
  # TODO: should this be cross-namespace?
  versionSourceRef:
    kind: ImagePolicy
    name: trivy-rc
    namespace: org-testorg # optional; defaults to the same namespace as the VUC CR

  # defaultVersion
  #
  # (Optional) When the operator detects a new matching target that has no version set or the version is `latest`, the version
  # will be set to `defaultVersion`, even outside an upgrade version. This happens only once, when a resource is
  # discovered for the first time.

  defaultVersion: "1.0.0"

  # versionUpgradeScheduleRef
  #
  # Source of the schedule information. This is a reference to a `VersionUpgradeSchedule` CR in the same namespace.
  # TODO: should this be cross-namespace?
  versionUpgradeScheduleRef:
    name: upgrade-stable-at-night

  # versionLock (still being discussed)
  #
  # Decides policy towards version changes of targeted objects, that were not introduced by the controller.
  #
  # It could be something simple like `True`, which means we lock current version, or `False`,
  # which means we don't. But it can be more sophisticated, say for example, it is an enum field
  # with these values:
  #
  # "None" - user may change version of the app, controller won't react. When reconciliation time comes,
  #          the target field version will be set by the controller.
  # "Corrective" - user may change version of the app, but during reconciliation, the controller will
  #                restore last version to it, but takes no responsibility for the damage that switching
  #                the versions may have caused
  # "Enforce" - user may not change version of the app, for controller installs countermeasures
  #             for version changes that blocks user actions on versions.
  versionLock: "None"

status: # (still being discussed)
  # observedGeneration mirrors the metadata.generation of the spec that this
  # status reflects. Essential for knowing if the status is up-to-date with
  # the latest desired state changes.
  observedGeneration: 1

  conditions:
    # Ready condition: Indicates if the controller is able to reconcile this
    # resource. False might mean invalid spec or other fundamental issues preventing reconciliation attempts.
    - type: Ready
      status: "True" # "True", "False", "Unknown"
      observedGeneration: 1
      lastTransitionTime: "2025-04-15T08:30:00Z"
      reason: "ReconciliationSucceeded" # CamelCase reason code, must present also errors related to referenced resources: like Schedule or versionSource missing or errored
      message: "VersionUpgradeConfig is operational" # Human-readable summary

    # Synced condition: Indicates if the target resources are currently at the
    # latest discovered version according to the configuration. False could mean an
    # upgrade is pending, failed, or paused by the schedule/policy.
    - type: Synced
      status: "False" # "True", "False", "Unknown"
      observedGeneration: 1
      lastTransitionTime: "2025-04-15T09:05:00Z"
      reason: "SyncPausedBySchedule" # TargetsSynced, TargetsSyncing, SyncPausedBySchedule, SyncPausedByNotBefore, SyncFailed
      message: "Upgrade paused, current time outside the scheduled window defined by utcSchedule."

  # lastReconciliationTime records when the controller last attempted to process
  # this resource. Useful for debugging timing issues.
  lastReconciliationTime: "2025-04-15T09:10:15Z"

  # versionSource provides details about the last check against the version source.
  versionSource:
    # lastCheckTime records when the version source (e.g., OCIRepository) was last checked.
    lastCheckTime: "2025-04-15T09:10:10Z"
    # latestDiscoveredVersion holds the most recent valid SemVer found in the source.
    # This might be different from the version currently applied to targets.
    latestDiscoveredVersion: "0.45.1"

  # scheduleSource provides specific timestamps when action will be taken based on the linked VUS object
  scheduleSource:
    # nextUpgradeWindowStart provides the calculated start time of the *next*
    # window during which upgrades are permitted according to the spec.
    nextUpgradeWindowStartTime: "2025-04-16T04:00:00Z" # Calculated from schedule
    # nextUpgradeWindowEnd provides the calculated end time of that next window.
    # (Typically start time + duration)
    nextUpgradeWindowEndTime: "2025-04-16T04:05:00Z" # Calculated from startTime + duration
    # lastCheckTime records when the schedule source was last checked.
    lastCheckTime: "2025-04-15T09:10:10Z"

  # TODO: think if the status is not too verbose, some info is redundant

  # upgradeAllowed indicates if, based on the suspend, current time and valid the controller
  # is currently permitted to perform an upgrade if one is needed.
  upgradeAllowed: false

  # lastAppliedVersion shows what was the version tried during the last version-applying sync
  lastAppliedVersion: "0.45.0"

  # lastApplyTime records when the lastAppliedVersion was attempted to be applied.
  lastApplyTime: "2025-04-14T04:03:00Z"

  # lastApplyResult provides the result of the last version application result.
  lastApplyResult: "PartiallySynced" # "Error", "AllSynced", "NoTargets"

  # targets provides a summary of the state related to the target resources.
  targets:
    # total indicates how many actual Kubernetes objects were matched by the
    # selectors/names defined in spec.targets during the last reconciliation.
    total: 5 # (e.g., 3 specific + 2 matched by label selector)

    # successful indicates how many objects were actually modified successfully in the last run.
    successful: 2

    # failed indicates how many targets didn't get a version change in the last reconciliation (ie. RBAC or ownership problems)
    failed: 1

    # pending shows targets that were discovered, but never had version applied
    pending: 2

    # inventory lists static (always all static targets listed in the .spec) and dynamic targets discovered
    # only during the last reconciliation run.
    # TODO: if the list is to be dynamic, it's probably enough to leave just kind and name
    inventory:
      # a static object with successful update
      - kind: App
        name: cluster3-trivy
        type: static
        status: Success # Unknown, ObjectNotFound, FieldNotFound, WriteError (when read only)
      # a static object with unsuccessful update - object was not found
      - kind: HelmRelease
        name: cluster2-trivy
        type: static
        status: ObjectNotFound # Unknown, ObjectNotFound, FieldNotFound, WriteError (when read only)
      # a dynamic object with successful update
      - kind: HelmRelease
        name: cluster45-trivy
        type: dynamic
        status: Success # Unknown, ObjectNotFound, FieldNotFound, WriteError (when read only)
      # a dynamic object that was discovered, but hasn't had any version applied yet
      - kind: HelmRelease
        name: cluster47-trivy
        type: dynamic
        status: Unknown # Unknown, ObjectNotFound, FieldNotFound, WriteError (when read only)
      # a dynamic object that was discovered, but the controller failed to apply the version (RBAC?)
      - kind: HelmRelease
        name: cluster48-trivy
        type: dynamic
        status: WriteError # Unknown, ObjectNotFound, FieldNotFound, WriteError (when read only)
```

#### How to know my resources is under auto-upgrade management?

Target objects must be able to easily identify that they are under management by a VUC. This is gonna be done
using labels and annotations. This will be also used to detect and resolve conflicting VUC ownership.

```yaml
kind: Any
metadata:
  labels:
    vuc.giantswarm.io/manager: my-vuc-object-1 # allows to easily filter out all objects managed by a VUC, detect that it's already under VUC management
  annotations:
    vuc.giantswarm.io/last-update-time: "2025-04-14T04:03:00Z" # allows to check when a version was last applied and detect stale management of a VUC
    vuc.giantswarm.io/last-update-version: "v1.2.3" # allows to check what was the last automatically set version, which might be already different than a version currently set
```

#### Full usage example

Objects provided by a user to deploy an app, a regular scenario:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: trivy
  namespace: org-testorg
spec:
  url: https://charts.aquasec.com
  interval: 1h
---
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: cluster1-trivy
  namespace: org-testorg
  labels:
    app: trivy
    stage: production
spec:
  chart:
    spec:
      chart: trivy
      version: "latest"
      sourceRef:
        kind: HelmRepository
        name: trivy
  # ... other fields ...
```

Now, a user wants to add automatic scheduled upgrades for the application.

Firs step, we define how to find the most recent relevant tag we need (for the app's helm chart). The
`ImageRepository` can be skipped and reused if it already exists:

```yaml
---
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: trivy-chart
  namespace: org-testorg
spec:
  image: https://charts.aquasec.com/trivy
  interval: 1h
  provider: generic
---
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: trivy-rc
  namespace: org-testorg
spec:
  imageRepositoryRef:
    name: trivy-chart
  policy:
    semver:
      range: ">=1.0.0"
    filterTags:
      pattern: ".*-rc.*"
```

Now, we either create or reuse a schedule we want:

```yaml
apiVersion: upgrade.giantswarm.io/v1alpha1
kind: VersionUpgradeSchedule
metadata:
  name: upgrade-monday-morning
  namespace: org-testorg
spec:
  valid:
    - from: "2025-06-01T00:00Z"
  upgradeWindows:
    - dayOfWeek: Mon
      time: "02:00Z"
      duration: 60m
```

Finally, we create a `VersionUpgradeConfig` that targets our `HelmRelease` and uses provided version and
schedule information:

```yaml
apiVersion: upgrade.giantswarm.io/v1alpha1
kind: VersionUpgradeConfig
metadata:
  name: trivy-helm-auto-upgrade
  namespace: org-testorg
spec:
  suspend: false
  serviceAccountName: automation
  interval: 5m
  targets:
    - kind: HelmRelease
      field: spec.chart.spec.version
      labelSelector:
        app: trivy
        stage: production
  versionSourceRef:
    kind: ImagePolicy
    name: trivy-rc
    namespace: org-testorg
  defaultVersion: "1.0.0-rc1"
  versionUpgradeScheduleRef:
    name: upgrade-monday-morning
  versionLock: "None"
```

The above configuration will:

- set the trivy Helm Chart version to `1.0.0-rc1` on the first reconciliation of the `VUC` resource, even if
  outside the upgrade window, because `defaultVersion` attribute is set
- keep checking for new chart releases matching the `.*-rc.*` pattern
- apply the newest version found to the target `HelmRelese`'s `spec.chart.spec.version` attribute only on
  Mondays between 2:00 and 3:00 UTC.

As a result, the target `HelmRelease` will be labeled and annotated to indicate it's under `VUC` management:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: cluster1-trivy
  namespace: org-testorg
  labels:
    app: trivy
    stage: production
    vuc.giantswarm.io/manager: trivy-helm-auto-upgrade # VUC object name
  annotations:
    vuc.giantswarm.io/last-update-time: "2025-06-02T02:05:00Z"
    vuc.giantswarm.io/last-update-version: "1.2.3-rc1"
```

## Notes

### Thoughts

- Flux already provides information about the last few helm releases, it might be useful to show it in order
  to make debugging problems easier https://fluxcd.io/flux/components/helm/helmreleases/#history-example
- What should we do when there's a version upgrade possible for a target, but the last known state of the
  versionSource is "failed"? Should we apply upgrades in that case? I think yes, as it's the rollout
  operator's problem to handle such problems.
- Q: Is it possible that the upgrade-operator can set just 1 Condition field in the status of the target and
  put all the relevant auto upgrade information there A: No, that won't work reliably
- Q: Is ImageRepository checking Helm Chart versions or Image?! A: Can work with both.
- Q: How many `ImageRepositories` should we expect to have to create per MC? A: Quick check on adidas' and
  ours MCs shows something in the range of 100-150, so not a problem.
