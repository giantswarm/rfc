---
creation_date: 2023-05-31
state: approved
---

# Simplify `baseDomain` usage in our applications

The `baseDomain` is the common suffix that we use as a base for the DNS records created for our clusters.
The meaning of the `baseDomain` is different in `vintage` and CAPI installations. In `vintage`, it contains information about the management cluster (it identifies a management cluster) while in CAPI installations, it doesn't contain any information about the management cluster.

For example in CAPI installation, if the `baseDomain` is `gaws.gigantic.io`, a cluster called `mycluster` will have its kubernetes API endpoint listening at `api.mycluster.gaws.gigantic.io`. It doesn't matter if the cluster is a management cluster or a workload cluster.

In `vintage`, if the `baseDomain` is `goku.germanywestcentral.azure.gigantic.io` (notice that it contains the name of the management cluster), the management cluster kubernetes API endpoint will be listening at `g8s.goku.germanywestcentral.azure.gigantic.io`.
While a workload cluster called `mycluster` will have its kubernetes API endpoint listening at `api.x6rtd.k8s.goku.germanywestcentral.azure.gigantic.io`.

There are different problems with our current approach.

## Problems

### Global value

We have made the `baseDomain` value available everywhere, and we have lost track of which apps depend on it or how they are using it.
It's global value that is passed around magically. Changing the `baseDomain` has unknown and potentially catastrophic consequences.

### Complex setup

We configure the `baseDomain` differently depending on how the app that needs the value is deployed:

- For apps that are part of [the app collections deployed to our Management Clusters](https://github.com/giantswarm/capa-app-collection), we pass [the `baseDomain` using the `config` repo](https://github.com/giantswarm/config/blob/main/default/apps/nginx-ingress-controller-app/configmap-values.yaml.template#L2).
- For [the default apps](https://github.com/giantswarm/default-apps-aws) (apps deployed to both Management Clusters and Workload Clusters), we store the `baseDomain` in a special configmap called `$clustername-cluster-values` created by `cluster-apps-operator` in CAPI installations and by `cluster-operator` in `vintage`. This configmap [is referenced from the `App` CR of the default apps](https://github.com/giantswarm/default-apps-aws/blob/master/helm/default-apps-aws/templates/apps.yaml#L38-L40).
- For other apps, we also store the `baseDomain` [in several app catalogs configuration](https://github.com/giantswarm/installations/blob/master/gohan/appcatalog/default-appcatalog-values.yaml#L5). That way the `baseDomain` is passed to all applications installed from those catalogs (Honeybadger has already stated that app catalog configuration may go away in the future).

### Differences between `vintage` and CAPI installations

The difference in the value for `baseDomain` between `vintage` and CAPI installations is sometimes confusing while working on applications that will be deployed to both kinds of installations.
The fact that we reuse the same variable name for values that could potentially contain different things (does it contain info about the management cluster or not?) is confusing and error-prone, adding complexity where this value is used.

### Different clusters in the same installation can't use different `baseDomain` values

We have several controllers reconciling workload clusters, and these controllers receive the `baseDomain` configuration value to create resources for the reconciled clusters.
Because we pass the `baseDomain` as a parameter to the controllers, all clusters in a single installation must share the same `baseDomain`. This has some big drawbacks

- Different workload clusters managed by the same management cluster can't use different domains easily. If the customer wants a workload cluster with a different baseDomain, they would have to create a CNAME for the new domain and pass special configuration for that specific cluster (they could also create a new management cluster).
- Workload clusters can't be moved to a different management cluster, the `baseDomain` creates a dependency between the management cluster and the workload cluster.

### Same variable name for different values

In our `installations` repository we save the `baseDomain` in the app catalog, so that this value is automatically passed to all apps from that catalog. For example, [on `goat` we have this value](https://github.com/giantswarm/installations/blob/master/gohan/appcatalog/default-appcatalog-values.yaml#L5)
```yaml
baseDomain: gtest.gigantic.io
```

But most applications expect the `baseDomain` to contain the cluster name as a prefix, like `mycluster.gtest.gigantic.io`.

These differences here and there are confusing.

## Proposal #1: Add `baseDomain` as an annotation to Cluster Custom Resource in CAPI installations

There are two types of applications running on the Management clusters that use the `baseDomain` value.
There are applications that reconcile CAPI Custom Resources, and there are other applications that need the Management cluster `baseDomain` for different things, like creating `Ingress` objects.

For the first group, instead of passing the `baseDomain` value as a parameter through the `config` repo, we could add a new annotation `"giantswarm.io/dns-zone"` to the `Cluster` Custom Resources instead.
That way, when reconciling clusters, our operators could read the annotation from the `Cluster` object instead of requiring to configure the `baseDomain` in the `config` repository.

```yaml
apiVersion: cluster.x-k8s.io/v1beta1
kind: Cluster
metadata:
  annotations:
    cluster.giantswarm.io/description: golem MC
    giantswarm.io/dns-zone: golem.gaws.gigantic.io
  labels:
    app: cluster-aws
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/version: 0.26.0
    application.giantswarm.io/team: hydra
    cluster-apps-operator.giantswarm.io/watching: ""
    cluster.x-k8s.io/cluster-name: golem
    giantswarm.io/cluster: golem
    giantswarm.io/organization: giantswarm
    helm.sh/chart: cluster-aws-0.26.0
  name: golem
  namespace: org-giantswarm
```

The `baseDomain` would still be used by the applications that we deploy to management clusters that don't reconcile clusters, because these applications need the DNS zone of the management cluster.
This variable could potentially be renamed to something like `managementClusterDNSZone` in the future to make clear its purpose, but it's not in the scope of this RFC to discuss this.

### Advantages

On top of reducing the usage of the global `baseDomain` value, there are other advantages when using this approach.

#### Custom Resources triggering changes rather than controllers

Moving configuration from operators to custom resources is always preferable. Starting by the obvious, the cluster configuration is right there explicitly in the `Cluster` Custom resource rather than hidden in controllers configuration.
Furthermore, if the value is part of the `Cluster` CR, it's the `Cluster` the one driving and triggering changes on cloud resources, allowing clusters to change or update their values independently of each other.
This is a better scenario than our current approach having the controller receive this configuration as a parameter, because changing the parameter would trigger changes in cloud resources on all clusters.

#### Reduce coupling

Controllers fetching the `baseDomain` value from the `cluster-values` configmap depend on the `cluster-apps-operator` or `cluster-operator` deployed and creating the configmap.
Using the value from the annotation instead of depending on the configmap reduces coupling between our controllers.

#### Potential to use different DNS hosted zones on the same Management Cluster

With our current approach, we configure the `baseDomain` at the installation level through the `config` repository, making the `baseDomain` shared for all clusters in a single installation.
If we move the value to be part of the `Cluster` CR, different clusters could potentially use different hosted zones, even on the same Management Cluster.

#### Migrate workload clusters to different management cluster

One side effect from this is that by decoupling the `baseDomain` from the Management Cluster would also help moving clusters between installations, if that would be desired.

#### Make kubectl-gs more reliable when creating client certificates for WCs

`kubectl-gs` could also use this annotation when creating client certificates for workload clusters.
Currently, it gets the cluster domain from the `Spec.ControlPlaneEndpoint.Host` property of the Cluster CR, which is not always accurate. Getting the domain from the annotation would fix it.

### Downsides

#### Migration

For the migration to this approach, we would need to annotate all `Cluster` Custom Resources to have the annotation.
We also would need to change our operators so that they read this value instead of the parameter they currently receive using the `config` repository.

This also means that our operators would add `cluster-api` as a Go dependency. From the list below, all operators but `dex-operator` already depend on `cluster-api`.

##### List of controllers that reconcile clusters and use the `baseDomain`

###### aws-resolver-rules-operator

It needs it to construct the k8s api endpoint of the cluster that's reconciling, so that it can create a Route53 Resolver Rule for it.

###### cluster-apps-operator

It needs it to store it in the `cluster-values` configmap that will be consumed by default apps of the cluster that's reconciling.

###### dex-operator

It needs it to configure dex for the cluster that's reconciling. The `baseDomain` passed to the app in the `config` repository is only used in `vintage` management clusters.
For CAPI clusters or `vintage` workload clusters, the controller loads the `cluster-values` configmap from the management cluster.
It should also take the value from the annotation instead.

###### dns-operator-*

It needs it to create the hosted zone and DNS records for the cluster that's reconciling.

###### irsa-operator

For CAPI clusters it loads the `cluster-values` configmap from the management cluster. It should also take the value from the annotation instead.

## Proposal #2: Set value in default-apps-* config instead of using `baseDomain` from the `cluster-values` configmap in CAPI installations

The `cluster-apps-operator` in CAPI installations, (and the `cluster-operator` in `vintage` installations) is creating a configmap called `$clustername-cluster-values` that contains values related to the workload cluster called `$clustername`.
One of these values is the `baseDomain` for that cluster.
This configmap is then added as [a config source in the `App` CRs created for the workload clusters default apps](https://github.com/giantswarm/default-apps-aws/blob/master/helm/default-apps-aws/templates/apps.yaml#L38-L40).

In CAPI installations, when installing the default apps in the `default-apps-$provider` app bundle, we can pass configuration values, [like we currently do for `cilium`](https://github.com/giantswarm/default-apps-aws/blob/master/helm/default-apps-aws/values.yaml#L10-L26).
This means that we can pass the `baseDomain` to the default apps that need it. There is no need to add a reference to the `cluster-values` configmap to the `App` CR of the default apps.

### Advantages

#### More explicit, less surprises

This way we know exactly which default apps depend on the `baseDomain` value, and we explicitly pass it, instead of relying on some mechanism that automagically passes the value.

#### Reduce coupling

Applications fetching this value from the `cluster-values` configmap depend on the `cluster-apps-operator` or `cluster-operator` being deployed and creating the configmap.
Using the value directly from the `default-apps-$provider` bundle instead of depending on the configmap reduces coupling between our apps.

#### Reduce complexity

We would completely eliminate one of the ways of configuring the `baseDomain`, by removing it from the `cluster-values` configmap.

#### Aligned with our GitOps strategy

All the configuration would be in the repository containing the default apps manifests, instead of this configmap being dynamically created by an operator.

#### No need to migrate cluster-apps-operator

If `cluster-aps-operator` wouldn't need the `baseDomain` anymore, we wouldn't need to migrate the operator to take the value from an annotation.

### Downsides

#### Verbosity in default apps bundle

We would need to explicitly pass the `baseConfig` to all the different apps that need it in the default apps bundle.

##### List of default apps using the `baseDomain` from the `cluster-values` configmap

###### cilium

It uses the `baseDomain` to talk to the k8s api. It already receives the `baseDomain` from the `default-apps-$provider` bundle, so there is no need to do anything here.

###### external-dns-app

It uses the `baseDomain` to filter which DNS records to take care of. We could do the same thing we do with `cilium` and pass the `baseDomain` in the `default-apps-$provider` bundle.

## Concerns raised during discussions and open questions.

- Would these proposals add more differences between `capi` and `vintage` installations?
- Could we default the new annotation somehow?


## Deadline

The RFC will be closed on the 04/05/2023.
