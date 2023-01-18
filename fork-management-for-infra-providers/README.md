# Fork Management for CAPI+Infra controllers

The purpose of this RFC is to specify how we will manage forked repositories for CAPI and infra providers such as CAPVCD, CAPA, CAPO etc.

## Problem Statement

We use open-source Kubernetes operators in our platform and we need to customize them at some points.

- We deploy them via the app platform so we need to bundle them as apps.
- We have our requirements regarding deployment/configuration specs (e.g. common labels, CRD management etc.) so we need to customize the manifests.
- We sometimes need to maintain some diffs in the core code since
  - We need hotfixes and we don't have time to wait for merges in upstream repositories.
  - We have a pretty specific temporary/permanent requirement and it is not possible to add it to upstream repositories. We must fight for keeping this diff as small/short-term as possible. 

We need to 
- define a fork management policy including repo management and branching strategies
- automate code syncs, image building and releases 

## Current status

### Repositories

We have 2 repositories per operator
1. Fork of the upstream repository 
- Examples:
  - https://github.com/giantswarm/cluster-api
  - https://github.com/giantswarm/cluster-api-provider-aws
  - https://github.com/giantswarm/cluster-api-provider-cloud-director
  - https://github.com/giantswarm/cluster-api-provider-gcp

1. A repository for bundling the operator as an app 
- Naming: https://github.com/giantswarm/\<fork-name\>-app
- Examples
  - https://github.com/giantswarm/cluster-api-app
  - https://github.com/giantswarm/cluster-api-provider-aws-app
  - https://github.com/giantswarm/cluster-api-provider-cloud-director-app
  - https://github.com/giantswarm/cluster-api-provider-gcp-app

### Syncing fork repositories

There is no common way.

In CAPVCD, since we have some diffs between our fork and upstream repo, we have a mechanism as follows:
- `main` branch of the repo is the same as the upstream one. We sync this branch by clicking `Sync fork` button in the UI.
- `giantswarm-main` branch of the repo contains our changes. We manually rebase it on top of `main` branch when necessary and open a new PR each time. The developer is supposed to resolve conflicts during rebasing.
 
### Bundling + Customization

There are some differences between repositories but the general structure in app repositories is as follows:

- We have Makefile + Bash scripts to
  - Check out a specific commit/branch of fork/upstream repo. [Example](https://github.com/giantswarm/cluster-api-provider-cloud-director-app/blob/adfc74115d9b7aeda60d885500122be3fb434d2e/Makefile.custom.mk#L14)
  - Generate base manifests by running scripts of the core repo
  - Customize base manifests with kustomization. [Example](https://github.com/giantswarm/cluster-api-provider-cloud-director-app/blob/adfc74115d9b7aeda60d885500122be3fb434d2e/Makefile.custom.mk#L19)
  - Update manifests under `helm` folder for the app. [Example](https://github.com/giantswarm/cluster-api-provider-cloud-director-app/blob/adfc74115d9b7aeda60d885500122be3fb434d2e/Makefile.custom.mk#L28)

When it is necessary to update the app content, developers are supposed to
- run make targets manually to update manifests and values in the app repo
- open a PR in the app repo

### Image Management

For some providers, we retag upstream images with retagger.
For some providers like CAPVCD, we build/push images manually.

## Design proposals

### 1. Repo management

#### 1.a Separate repositories for fork and app

We can have two repositories per operator. One is only fork of upstream and the other one is for only bundling it as an app.

#### 1.b One repository for fork and app

We can maintain bundling and customization logic in the same repo.

#### Decision

- `1.a` is the current situation.
- `1.b` will lead to many conflicts with the upstream repository and it will be hard to automate conflict resolution.

`1.a` is decided.

---

### 2. Branching strategy in fork repo

#### 2.a main vs giantswarm-main

We can maintain two branches in the fork repo. 
- `main` will be just the same as `main` of upstream repository. This branch can be synced automatically.
- `giantswarm-main` will contain our changes if necessary. 

The update flow will be
- First update `main`
- Then rebase `giantswarm-main`

#### 2.b only main

We can maintain only one `main` branch including our changes and use `git merge` to apply upstream changes.

#### Decision

`2.a` is decided.

---

### 3. Image building

#### 3.a Not building images 

It is not possible to rely on only retagged versions of containers provided by the upstream community since we want to be able to apply our changes to code base.

#### 3.b Building/Pushing images in the fork repo

We can add an image building/pushing mechanism to fork repository.

- This will increase the diff between fork and upstram repo but it will be only some manifests under `.github` or `.circleci` folders.
- This will allow developers to verify container building while developing features.

#### 3.c Building/Pushing images in the app repo

We can build/push images while syncing the app repo. That works pretty well while consuming upstream repo but it will make less sense when having our own fork. 

#### Decision

`3.b` is decided.

---

### 4. Where to build the images

#### 4.a Github Actions

#### 4.b CircleCI

#### Decision

Since we build/push images via CircleCI for our other repositories, `4.b` is decided.

---

### 5. Sync logic in the app repo

Because of the decisions in sections 1 and 2, in the app repo, the sync mechanism should be able to consume any commit/branch from fork/upstream repo. 
See https://github.com/giantswarm/cluster-api-provider-cloud-director-app/blob/adfc74115d9b7aeda60d885500122be3fb434d2e/Makefile.custom.mk#L7

