# Application ownership models

A lifecycle of an Kubernetes application could be roughly split into the following stages and sub-stages:
- Development
- Release engineering, which could be broken down to:
  - Building
  - Testing
  - Packaging
  - Delivery (deployment, upgrades, removal)
- Operations, which could be broken down to:
  - Investigating issues
  - Improving performance
  - On-call
  - Postmortems
  - Root cause analysis

Additionally, while for the most of applications it's obvious which team can and should take care of its lifecycle, for some apps that is not very clear, as multiple teams have equally important stakes in it.

Based on the above, we can define two different criteria for defining application ownership models:
- What stages of the application lifecycle are owned by a team?
- Is there one or more Giant Swarm teams that can be considered owners of the application?

## 1. Application lifecycle ownership

We can define two high-level application ownership models:
- Full application ownership
- Partial application ownership, usually including release engineering (full or partial) and operations. This is typical for upstream applications where the development is done outside of Giant Swarm.

### 1.1. Full application lifecycle ownership

(Almost) Full application ownership includes all stages of the application lifecycle.

Development is done by team members.

Release engineering is done by team members who are using RelEng platform provided by Giant Swarm RelEng teams.

Operations are handled by the team members, including business hours as a part of team on-call, and non-business hours as a part of team/area on-call. There are few caveats here:
- The non-business hours on-call is currently shared with other teams from the same area (hence "almost" full ownership), which is done for the sake of not overwhelming on-callers with frequent night shifts.
- Ideally, if a team has enough people and we have state-of-the-art monitoring and alerting, meaning that there are next-to-none false positive alerts (for example caused by alerts from other team's components), the team can own 24h on-call for the application.

### 1.2. Partial application lifecycle ownership

Partial application ownership means that application development is done outside of Giant Swarm, therefore this is the case of upstream applications that we are deploying to our clusters.

To name a few examples, we run, but do not develop, Prometheus, Grafana, Cluster API controllers, Kyverno, different CNI, CSI, CPI apps, then core Kubernetes components, such as API server, scheduler, controller manager, etcd, kubelet, etc.

Partial application ownership of these components means that a Giant Swarm team owns:
- Release engineering, fully or partially;
- Operations, fully or partially, depending if the team has sole or shared ownership of the application, which is discussed in the next section.

**Release engineering is owned fully** in case of forked projects, where Giant Swarm team builds the application from the forked repository, then tests, packages and finally delivers it.

**Release engineering is owned partially** when Giant Swarm team does not build the app, but, for example, re-tagged container image is used. Here we have two cases:
- Giant Swarm team is packaging the app as a Helm chart in the app repository, by building required Helm templates for deploying re-tagged container images and optionally using existing upstream Kubernetes manifests instead of writing Helm templates from scratch.
- Giant Swarm is repackaging or importing existing upstream Helm charts into Giant Swarm application repositories.

## 2. Sole or shared application ownership

While different application ownership models based on application lifecycle stages are relatively clear and it's obvious which model is used for every application, for some apps is much less evident which team should own them, and if there can even be just one owning team, or multiple teams cannot be avoided due to shared nature of the app.

Additionally, while application lifecycle stages split the app ownership between external (upstream) and internal (Giant Swarm) teams, sole or shared ownership is about how we handle app ownership internally within Giant Swarm.

### 2.1. Sole application ownership

The is the classical and usually the obvious case. A Giant Swarm team develops the application, in case of full application lifecycle ownership described in the previous section, or the team takes care of release engineering and operations for the app, in case of partial application lifecycle ownership described above.

### 2.2. Shared application ownership

And this is the tricky part, one of the main reasons for which this whole RFC is written.

Shared application ownership applies in some cases of partial application lifecycle ownership, so in a nutshell, the question here is - which Giant Swarm team owns some upstream application? Can it even be one team, or multiple teams must share ownership? If multiple teams share ownership, how does that work in practice?

There is no silver bullet for all upstream applications, so here we need a clear and robust, but also flexible ownership model.

Before trying to come up with some definition, let's first check few examples.

#### 2.2.1. Examples of shared applications

While there are more examples, let's take the following two that should paint the picture and describe the issue of shared ownership clearly enough.

**Cluster API provider-independent controllers**

There are three CAPI controllers that are equally used by KaaS teams (Rocket, Hydra, Clippy) - core, kubeadm control plane and kubeadm bootstrap controller. They are all packaged together in the cluster-api-app. All KaaS teams have equal stakes in this app and equal responsibilities.

Which teams is responsible for maintaining the application repository, improving it, automating it, taking care of renovate and other automated pull requests? Which teams takes care of upgrading the app to the latest upstream? Every team for themselves when they have a need? This is not working very efficiently.

**Kubernetes components**

We could say that deploying and using Kubernetes is sort of what we all do for living, right?

Quick reminder that here we are talking about partial application lifecycle ownership, so release engineering and operations, where we can't really say that we do former one, so the latter one is interesting here.

All teams write or package operators that get scheduled to some node, operators that use and maybe sometimes hammer API server, deploy few or few hundreds of CRDs that case clusters to be overloaded, etc.

Let's say that all teams are more or less similarly using all (or most of) Kubernetes components. In that case a single team owning operations for those components would be ~~ludacris~~ ludicrous, and that didn't really work nicely when we tried it.

#### 2.2.2. Implementing shared application ownership in practice

So how do we implement shared application ownership in practice?

Teams own apps with sole application ownership model. And multiple teams take turns, i.e. multiple teams participate in the rotation of sole application ownership.

When a team is assigned to be sole app owner that means that the team takes care of app's release engineering and operations (on-call, postmortems, etc).

How frequently the ownership is rotated depends on the app, and is decided on a case by case basis by the interested teams, but in most cases the app ownership should be passed to the next team every few months to half a year, depending on the release cadence of the app. Less than a month is probably too often, more than half a year could lead to folks falling out of practice (important for operations) or even mean that some team doesn't get to own the app as team structure changes.

This shared application ownership model could be applied to the above examples in the following way (made up examples, not suggestions in the RFC):
- Cluster API ownership is rotated between KaaS teams every 2 months. Within this time frame the team will deal with multiple minor and patch releases for which the release engineering work is required. Also, the rotation is relatively frequent, so everybody will be up-to-date when it comes to operations.
- Kubernetes components are rotated between all Giant Swarm teams. Considering that here we are almost not doing any release engineering work, in terms of building, testing and packaging Kubernetes itself, we are mostly talking about operations work for main Kubernetes components and (probably and preferably) upgrading Kubernetes clusters (depending on how we define ownership here). Since all this is a work with which all teams should be familiar with, sharing and rotting that work among all teams removes the burden from a single team and all teams equally share the load, knowledge and experience.

## 3. Final application ownership matrix

When we combine the above criteria, imagine a matrix with one criteria being the vertical, and the other one being horizontal, we have the following application ownership models:
1. Single team with full application lifecycle ownership
2. Single team with partial application lifecycle ownership
3. Multiple teams with partial application lifecycle ownership, where teams take turns as sole application owners every X months.
