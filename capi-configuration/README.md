# Configuration management with Cluster API

This RFC describes how we can handle configuration management with Cluster API - focussing on defaulting, upgrades and interactions.

## Context

During our transition to `cluster-api` we have decided to no longer directly couple operator versions to cluster versions.
The version of a cluster should completely be determined by the configuration of the cluster.
An example to show this changed approach is the following:
- Cluster `deu01` has configuration `X` and is reconciled by `capi-controller` in version `1.1.0`.
- `capi-controller` is updated to version `1.2.0`. Cluster `deu01` remains completely unchanged.
- A new cluster `peu01` with configuration `X` is exactly the same as `deu01`.
- The configuration of `deu01` is changed to `Y` which causes the cluster to upgrade.
The lifecycle of the cluster is therefor fully determined by its configuration and no longer determined by the operator reconciling it.

_A new concept for Giant Swarm releases is completely decoupled from the operators and only consists of cluster configuration!_

## Problem Statement

We need to ...
1. be able to define Giant Swarm releases as sets of configuration.
2. be able to create Giant Swarm clusters in a repeatable and reliably way.
3. be able to upgrade Giant Swarm clusters in a repeatable way with `cluster-api`.
4. be able to default Giant Swarm clusters through all our user interfaces consistently.

We want to ...
1. decouple managed applications from strict release flows.
2. give customers greater control over how their clusters are defaulted.
3. enable customers to have more agency in upgrading individual components.
4. give a lower barrier of entry for customers to deeply interact with our product.

## Git-Ops approach

We have already taken steps to manage configuration for our components in management clusters through open source gitops tools.
This has set a precedent for gitops management for configuration in other areas as well.

Our customers generally desire to work with an `Infrastructure As Code` approach which is extendended by currently available open source gitops tooling.

**This RFC will exclusively deal with the impact of using a gitops driven approach in the following sections.**

## Configuration structure

There are many different possible ways to structure the configuration which is used to create the clusters.
The goal here is to provide one way that we think _can_ work and then iterating on it - we do not want to box ourselves in.

### Cluster-api fundamental structure

There are some links between and some fields in `cluster-api` custom resources which are essential.
These fields can not be inferred from a webhook without context knowledge.
It is therefor necessary to supply these values _immediately_ when the custom resource is created (e.g. `kubectl-gs` or `happa` needs to fill them).

We can look at a valid `MachinePool` custom resource to determine its fundamental structure:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: capa-mp-0
spec:
  clusterName: capa
  replicas: 2
  template:
    spec:
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha3
          kind: KubeadmConfig
          name: capa-mp-0
      clusterName: capa
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
        kind: AWSMachinePool
        name: capa-mp-0
      version: v1.16.8
```
- We can not infer `apiVersion` as it's an essential field.
- We can not infer `kind` as it's an essential field.
- We can not infer `metadata.name` as it's required to create the custom resource.
- We can not infer `spec.clusterName` as it's unique to the created cluster.
- We can not infer `spec.template.spec.bootstrap.configRef.name` as it's unique to the cluster.
- We can not infer `spec.template.spec.infrastructureRef.configRef.name` as it's unique to the cluster.

All other values can either be inferred from other information in the custom resource or from default values.

Therefor the **minimal** custom resource which would have to be submitted by a client should be:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: capa-mp-0
spec:
  clusterName: capa
  template:
    spec:
      bootstrap:
        configRef:
          name: capa-mp-0
      infrastructureRef:
        name: capa-mp-0
```

This minimal custom resource can also be represented as a template which will remain valid throughout the lifecycle of `v1alpha3` in this case:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: {{clusterID}}-mp-0
spec:
  clusterName: {{clusterID}}
  template:
    spec:
      bootstrap:
        configRef:
          name: {{clusterID}}-mp-0
      infrastructureRef:
        name: {{clusterID}}-mp-0
```
This template is going to be stable for any `v1alpha3` cluster and would only need minimal changes to be stable for `v1alpha4`.

### Cluster-api base files

We need to default a big set of custom resources with `cluster-api`.
These custom resources need to be created and defaulted in a consistent way.
The approach we follow here is to have a single source of truth which is as complete as possible.

`base files` are our static defaulting values - any webhook or tool which does defaulting should use them as the source of truth.

Let's look at an example to clarify the technical implications.
A valid `MachinePool` CR in `v1alpha3` can look like this:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: capa-mp-0
spec:
  clusterName: capa
  replicas: 2
  template:
    spec:
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha3
          kind: KubeadmConfig
          name: capa-mp-0
      clusterName: capa
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
        kind: AWSMachinePool
        name: capa-mp-0
      version: v1.16.8
```
From this custom resource we can now extract the values which are static and configurable.
So values which a customer might want to change the default of _and_ which we can default statically independent of any other content in the custom resource.

In this particular case there are two values which are both static and configurable:
- `spec.replicas`
- `spec.template.spec.version`

We can now construct a `ConfigMap` with these values which are then going to be used by any defaulting tool/webhook:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: machinepool-21-0-0
  namespace: giantswarm
data:
  spec:
    replicas: 3
    template:
      spec:
        version: v1.21.4
```
It is important to note that a assumption is that **no** values in the base file are immutable!

### Cluster-api context dependent values

We have some cases in `cluster-api` where a value in a custom resource is neither part of the fundamental structure nor is it easy to statically default.

These values are usually highly dependent on the context in which the cluster is created in.
For example the `CIDR` in which the cluster is created.
We currently assume that these values will be defaulted by custom webhooks or operators with significant provider specific domain knowledge.

### Putting together a Giant Swarm release

A Giant Swarm releases is just a set of `cluster-api` base files as defined previously with added `apps`.

The following folder structure would be contained in `giantswarm/example-customer`:
```yaml
aws:
  v21.0.0:
    base:
      cluster.yaml # configmap containing the base file (defined above)
      aws-cluster.yaml
      machinepool.yaml
      awsmachinepool.yaml
      ...
      net-exporter.yaml # configmap containing version information for defaulting!
    overlay:
      special-overlay.yaml # Added by customer to e.g. overlay a different flatcar version!
  v22.0.0:
    base:
      ...
    overlay:
      ...
```

In the management cluster a release is then simply a set of configmaps.
The configmaps for e.g. release `v21.0.0` will be applied through argoCD by taking the `base` configmaps, applying any `overlay` from a customer and then deploying them.

As shown in previous examples these configmaps would contain the release in their name (e.g. `machinepool-21-0-0`).
Any in-cluster webhook or operator can then easily navigate to these configmaps to look up defaults for a cluster.

A cluster creation workflow can now look as follows:
1. Client (e.g. `happa`) submits `--dry-run` with `fundamental` custom resources to management cluster.
2. Mutating webhooks take information from `base file` configmaps to default.
3. Client receives fully defaulted custom resources and allows users to make manual changes.
4. Client submits custom resources
5. Cluster is created.

A cluster upgrade workflow can then look like this:
1. Client changes cluster version label.
2. `upgrade-operator` reads `base file` configmaps according to the new version.
3. `upgrade-operator` starts replacing fields with new configuration from configmaps.

## Going gitops all the way

A next step in `gitops` adoption would be the addition of having the cluster custom resources in `gitops` as well.
So the shared git repository would contain not only release information but also the clusters themselves.

```yaml
gauss: # installation
  peu01: #clusterID
    base: # managed fully by GS
      cluster.yaml
      ...
      cert-exporter.yaml # default app
    overlay: # overwrites by customer
      cluster.yaml
      ...
      kong.yaml # non default app
aws: # releases as mentioned before
  v21.0.0:
  ...
```

Interaction with this repository could then be improved by adding functionality to our CLI `kubectl-gs`.

Cluster creation would become a `pull request` which commits code generated by `kubectl-gs`.

Upgrading a cluster is a bit more complex: Upgrades become a overwrite of configuration from the release to the `base` folder.
We can show this with a `MachinePool` example:
```yaml
# gauss/peu01/machinepool.yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: peu01-mp-0
spec:
  clusterName: peu01
  replicas: 2
  template:
    spec:
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha3
          kind: KubeadmConfig
          name: peu01-mp-0
      clusterName: peu01
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
        kind: AWSMachinePool
        name: peu01-mp-0
      version: v1.16.8
```
The upgrade to version `v22.0.0` would now be done by overwriting from `aws/v21.0.0/base/machinepool.yaml` + `aws/v21.0.0/overlay/machinepool.yaml`.
For this example we assume the `overlay` is empty and the `base` is as follows:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: machinepool-21-0-0
  namespace: giantswarm
data:
  spec:
    replicas: 3
    template:
      spec:
        version: v1.21.4
```
Then the resulting pull request for `gauss/peu01/machinepool.yaml` would change:
```yaml
# gauss/peu01/machinepool.yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: peu01-mp-0
spec:
  clusterName: peu01
  replicas: 3
  template:
    spec:
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha3
          kind: KubeadmConfig
          name: peu01-mp-0
      clusterName: peu01
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
        kind: AWSMachinePool
        name: peu01-mp-0
      version: v1.21.4
```

## Enabling customer access

We have to be able to give customers access to the `git` source in a gitops setup in order to allow effective modification of any configuration.

We already have a shared repository in the Giant Swarm organization with each customer individually.
It is therefore logical to utilize this shared repository as a source for gitops related data.

## Enabling customer collaboration

We can lower the barrier to entry by using a repository which is already shared with a customer which they are already familiar with.

The following setup can allow us to maintain a high degree of control:
- Make the account engineer assigned to the customer a mandatory reviewer
- Utilize `CODEOWNERS` files to split responsibilities between Giant Swarm teams
- Allow the customer to make `Pull Requests` but not self approve
- Allow all Giant Swarm employees to review and approve `Pull Requests`
- Require at least one approval before merging

The desired outcome would be increased involvement of our customers in their own configuration.

