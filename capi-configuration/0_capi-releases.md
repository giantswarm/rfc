# Releases as gitops managed configmaps

## Problem Statement

We need to ...
1. be able to define Giant Swarm releases as sets of configuration.
2. be able to create Giant Swarm clusters in a repeatable and reliable way.
3. be able to upgrade Giant Swarm clusters in a repeatable way with `cluster-api`.
4. be able to default Giant Swarm clusters through all our user interfaces consistently.

We want to ...
1. decouple managed applications from strict release flows.

## gitops approach

We have already taken steps to manage configuration for our components in management clusters through open source gitops tools.
This has set a precedent for gitops management for configuration in other areas as well.

Our customers generally desire to work with an `Infrastructure As Code` approach which is extended by currently available open source gitops tooling.

**This RFC will exclusively deal with the impact of using a gitops driven approach in the following sections.**

## Configuration structure

There are many different possible ways to structure the configuration which is used to create the clusters.
The goal here is to provide one way that we think _can_ work and then iterating on it - we do not want to box ourselves in.

### Cluster-api fundamental structure

There are some links between and some fields in `cluster-api` custom resources which are essential.
These fields can not be inferred from a webhook without context knowledge.
It is therefore necessary to supply these values _immediately_ when the custom resource is created (e.g. `kubectl-gs` or `happa` needs to fill them).
We therefore define `fundamental templates` as minimal templates which have to be submitted to create a working cluster.

We can look at a valid `MachinePool` custom resource to determine its fundamental structure:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: capa-mp-0 # This is taken from upstream, Giant Swarm would use an ID like `eump1`.
  namespace: my-org
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

Therefore the **minimal** custom resource which would have to be submitted by a client should be:
```yaml
apiVersion: cluster.x-k8s.io/v1alpha3
kind: MachinePool
metadata:
  name: capa-mp-0
  namespace: my-org
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
  name: {{machinePoolID}}
  namespace: {{orgNamespace}}
spec:
  clusterName: {{clusterID}}
  template:
    spec:
      bootstrap:
        configRef:
          name: {{machinePoolID}}
      infrastructureRef:
        name: {{machinePoolID}}
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
  name: eump1
  namespace: my-org
spec:
  clusterName: capa
  replicas: 2
  template:
    spec:
      bootstrap:
        configRef:
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha3
          kind: KubeadmConfig
          name: eump1
      clusterName: capa
      infrastructureRef:
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
        kind: AWSMachinePool
        name: eump1
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
It is important to note that an assumption is that **no** values in the base file are immutable!

### Cluster-api context dependent values

We have some cases in `cluster-api` where a value in a custom resource is neither part of the fundamental structure nor is it easy to statically default.

These values are usually highly dependent on the context in which the cluster is created.
For example the `CIDR` in which the cluster is created.
We currently assume that these values will be defaulted by custom webhooks or operators with significant provider specific domain knowledge.

### Putting together a Giant Swarm release

A Giant Swarm release is just a set of `cluster-api` base files as defined previously with added `apps`.

The following folder structure would be contained in `giantswarm/releases`:
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
      ... # For easier templating of shared values!
  v22.0.0:
    base:
      ...
    overlay:
      ...
```

In the management cluster a release is then simply a set of configmaps.
The configmaps for e.g. release `v21.0.0` will be applied through argoCD by taking the `base` configmaps.

As shown in previous examples these configmaps would contain the release in their name (e.g. `machinepool-21-0-0`).
Any in-cluster webhook or operator can then easily navigate to these configmaps to look up defaults for a cluster.

A cluster creation workflow can now look as follows:
1. Client (e.g. `happa`) submits `--dry-run` with `minimal` custom resources to management cluster.
2. Mutating webhooks take information from `base file` configmaps to default.
3. Client receives fully defaulted custom resources and allows users to make manual changes.
4. Client submits custom resources
5. Cluster is created.

A cluster upgrade workflow can then look like this:
1. Client changes cluster version label.
2. `upgrade-operator` reads `base file` configmaps according to the new version.
3. `upgrade-operator` starts replacing fields with new configuration from configmaps.
