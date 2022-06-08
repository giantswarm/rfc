# Cluster API custom resource monitoring

<!-- toc -->
- [Glossary](#glossary)
- [Problem statement](#problem-statement)
- [Cluster API state metrics](#cluster-api-state-metrics)
  - [Infrastructure provider specific metrics](#infrastructure-provider-specific-metrics)
    - [Variant 1: all providers in one generic CASM instance](#variant-1-all-providers-in-one-generic-casm-instance)
    - [Variant 2: one CASM instance per infrastructure provider](#variant-2-one-casm-instance-per-infrastructure-provider)
    - [Variant 2: one CASM instance per infrastructure provider plus one CASM instance for CAPI core](#variant-2-one-casm-instance-per-infrastructure-provider-plus-one-casm-instance-for-capi-core)
- [kube state metrics](#kube-state-metrics)
  - [Variant 1: specific <code>kube-state-metrics</code> configuration for the already existing <code>kube-state-metrics-app</code>](#variant-1-specific-kube-state-metrics-configuration-for-the-already-existing-kube-state-metrics-app)
    - [Pros](#pros)
    - [Cons](#cons)
  - [Variant 2: dedicated <code>kube-state-metrics</code> on management cluster](#variant-2-dedicated-kube-state-metrics-on-management-cluster)
    - [Variant 2.1: dedicated <code>kube-state-metrics</code> instance on management cluster for all CAPI providers](#variant-21-dedicated-kube-state-metrics-instance-on-management-cluster-for-all-capi-providers)
    - [Variant 2.2: dedicated <code>kube-state-metrics</code> instance on management cluster per CAPI providers](#variant-22-dedicated-kube-state-metrics-instance-on-management-cluster-per-capi-providers)
    - [Variant 2.3: two dedicated <code>kube-state-metrics</code> instances on management cluster per CAPI providers](#variant-23-two-dedicated-kube-state-metrics-instances-on-management-cluster-per-capi-providers)
    - [Pros](#pros-1)
    - [Cons](#cons-1)
- [Conclusion](#conclusion)
<!-- /toc -->

This RFC motivates the setup of a monitoring solution for Cluster API related CRs.

## Glossary

- Infrastructure providers - Cluster API infrastructure implementation for e.g. AWS (CAPA), OpenStack (CAPO), Google Compute Platorm (CAPG), ...
- `cluster-api-state-metrics` (CASM)
- `kube-state-metrics` (KSM)
- `CustomResourceStateMetrics` configuration is the format which KSM accept to understand how metrics from CRs have to be interpreted ([upstream documentation](https://github.com/kubernetes/kube-state-metrics/blob/master/docs/customresourcestate-metrics.md))
- Management Cluster (MC) is the Kubernetes Cluster where CAPI components are deployed and which is responsible for creating new Kubernetes Clusters (WCs)
- Workload Cluster (WC)

## Problem statement

As Cluster Operator we want to get know the state of any Cluster API related object (no matter if Cluster API Core or infrastructure provider specific).

As different states have impact on the expected behavior of the reconciliation e.g.

- A cluster upgrade won't finish successful if an already existing OpenStackMachine is in an error state (even if the machine is in a transient error).
- It's possible to set nearly all Cluster API related objects into a `paused` state to skip reconciliation for that - primary done by humans.

All these states might lead to different kind of troubleshooting sessions and possibly issues on customer side.

## Cluster API state metrics

As in the past `kube-state-metrics` only takes care of Kubernetes resources and not about `CustomResources` and all existing Cluster API controllers don't have object related metrics yet, [`cluster-api-state-metrics`](https://github.com/mercedes-benz/cluster-api-state-metrics) was created by Mercedes-Benz.

The CASM code will be contributed to the Cluster API project (Process can be tracked in [issue #6458](https://github.com/kubernetes-sigs/cluster-api/issues/6458)).

### Infrastructure provider specific metrics

Currently CASM only provide metrics of Cluster API Core components (e.g. `clusters`, `kubeadmcontrolplanes`,`machinedeployments`,`machines` or `machinesets`) and it's currently not clear how infrastructure provider specific metrics can be added/generated once the entire code base is living under `kubernetes-sigs/cluster-api`.

But as the code isn't that complex it's very easy to extend the existing implementation to support infrastructure provider specific metrics.

Beside generated changes in `go.mod` and `go.sum` only the following changes are needed to add the two new metrics `capi_openstackcluster_created` and `capi_openstackcluster_paused` into CASM.

```diff
diff --git a/pkg/store/factory.go b/pkg/store/factory.go
index f61a556..2892387 100644
--- a/pkg/store/factory.go                    
+++ b/pkg/store/factory.go                                                                        
@@ -7,6 +7,8 @@ import (                                                                          
        "k8s.io/client-go/rest"      
        "k8s.io/kube-state-metrics/v2/pkg/customresource"
        "k8s.io/kube-state-metrics/v2/pkg/options"                                                                                                                                                  
+       infrav1 "sigs.k8s.io/cluster-api-provider-openstack/api/v1alpha4"
        clusterv1 "sigs.k8s.io/cluster-api/api/v1alpha4"          
        controlplanev1 "sigs.k8s.io/cluster-api/controlplane/kubeadm/api/v1alpha4"
        "sigs.k8s.io/controller-runtime/pkg/client"                             
@@ -17,6 +19,8 @@ var scheme = runtime.NewScheme()                              
 func init() {                                                                                    
        _ = clusterv1.AddToScheme(scheme)                                                         
        _ = controlplanev1.AddToScheme(scheme)
+       _ = infrav1.AddToScheme(scheme)
        // +kubebuilder:scaffold:scheme
 }       
  
@@ -29,6 +33,8 @@ func Factories() []customresource.RegistryFactory {
                &MachineDeploymentFactory{},                                                                                                                                                        
                &MachineSetFactory{},                                                             
                &MachineFactory{},
+               &OpenStackClusterFactory{},                                                       
        }                                                                                         
 }   
```

```go
package store

import (
 "context"

 metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
 "k8s.io/apimachinery/pkg/runtime"
 "k8s.io/apimachinery/pkg/watch"
 "k8s.io/client-go/tools/cache"
 "k8s.io/kube-state-metrics/v2/pkg/metric"
 generator "k8s.io/kube-state-metrics/v2/pkg/metric_generator"
 infrav1 "sigs.k8s.io/cluster-api-provider-openstack/api/v1alpha4"
 capierrors "sigs.k8s.io/cluster-api/errors"
 "sigs.k8s.io/cluster-api/util/annotations"
 "sigs.k8s.io/controller-runtime/pkg/client"
)

var descOpenStackClusterLabelsDefaultLabels = []string{"namespace", "openstackcluster"}

type OpenStackClusterFactory struct {
 *ControllerRuntimeClientFactory
}

func (f *OpenStackClusterFactory) Name() string {
 return "openstackcluster"
}

func (f *OpenStackClusterFactory) ExpectedType() interface{} {
 return &infrav1.OpenStackCluster{}
}

func (f *OpenStackClusterFactory) MetricFamilyGenerators(allowAnnotationsList, allowLabelsList []string) []generator.FamilyGenerator {

 return []generator.FamilyGenerator{
  *generator.NewFamilyGenerator(
   "capi_openstackcluster_created",
   "Unix creation timestamp",
   metric.Gauge,
   "",
   wrapOpenStackClusterFunc(func(osc *infrav1.OpenStackCluster) *metric.Family {
    metrics := []*metric.Metric{}

    if !osc.CreationTimestamp.IsZero() {
     metrics = append(metrics, &metric.Metric{
      LabelKeys:   []string{},
      LabelValues: []string{},
      Value:       float64(osc.CreationTimestamp.Unix()),
     })
    }

    return &metric.Family{
     Metrics: metrics,
    }
   }),
  ),
  *generator.NewFamilyGenerator(
   "capi_openstackcluster_paused",
   "The openstackcluster is paused and not reconciled.",
   metric.Gauge,
   "",
   wrapOpenStackClusterFunc(func(osc *infrav1.OpenStackCluster) *metric.Family {
    paused := annotations.HasPausedAnnotation(osc)
    return &metric.Family{
     Metrics: []*metric.Metric{
      {
       LabelKeys:   []string{},
       LabelValues: []string{},
       Value:       boolFloat64(paused),
      },
     },
    }
   }),
  ),
 }
}

func (f *OpenStackClusterFactory) ListWatch(customResourceClient interface{}, ns string, fieldSelector string) cache.ListerWatcher {
 ctrlClient := customResourceClient.(client.WithWatch)
 return &cache.ListWatch{
  ListFunc: func(opts metav1.ListOptions) (runtime.Object, error) {
   openStackClusterList := infrav1.OpenStackClusterList{}
   opts.FieldSelector = fieldSelector
   err := ctrlClient.List(context.TODO(), &openStackClusterList, &client.ListOptions{Raw: &opts, Namespace: ns})
   return &openStackClusterList, err
  },
  WatchFunc: func(opts metav1.ListOptions) (watch.Interface, error) {
   openStackClusterList := infrav1.OpenStackClusterList{}
   opts.FieldSelector = fieldSelector
   return ctrlClient.Watch(context.TODO(), &openStackClusterList, &client.ListOptions{Raw: &opts, Namespace: ns})
  },
 }
}

func wrapOpenStackClusterFunc(f func(*infrav1.OpenStackCluster) *metric.Family) func(interface{}) *metric.Family {
 return func(obj interface{}) *metric.Family {
  openStackCluster := obj.(*infrav1.OpenStackCluster)

  metricFamily := f(openStackCluster)

  for _, m := range metricFamily.Metrics {
   m.LabelKeys = append(descOpenStackClusterLabelsDefaultLabels, m.LabelKeys...)
   m.LabelValues = append([]string{openStackCluster.Namespace, openStackCluster.Name}, m.LabelValues...)
  }

  return metricFamily
 }
}
```

#### Variant 1: all providers in one generic CASM instance

##### Pros

- Resources can be enabled via an already existing command line flag. Adopting this in a helm-chart becomes quite easy as we already have some provider specific flags on other shared components.

##### Cons

- As different CAPI versions might exist on different kind of MCs we have to ensure that CASM is downwards compatible over multiple providers/teams.
- Transitive dependencies from multiple providers will cause issues.

#### Variant 2: one CASM instance per infrastructure provider

To separate the code of different providers it's possible to create an own fork per infrastructure provider or setup different main-branches per provider.

##### Pros

- Code ownership is handled per provider, which reflects the separation of our current teams.
- Every CAPI related CR is monitored by one single App.

##### Cons

- Some code maintenance must be done multiple times.

#### Variant 2: one CASM instance per infrastructure provider plus one CASM instance for CAPI core

##### Pros

- Cross-provider related components (CAPI core) are shared via one dedicated app.

##### Cons

- Waste of resources as two versions of CASM are deployed in management clusters.

## kube state metrics

With version [`v2.5.0`](https://github.com/kubernetes/kube-state-metrics/releases/tag/v2.5.0) of `kube-state-metrics` it's now possible to create metrics from custom resources by defining a configuration per metric.

As of now (`v2.5.0`) it's not possible to create metrics for non-numbered fields, e.g.:

```yaml
kind: CustomResourceStateMetrics
spec: 
  resources: 
    - groupVersionKind: 
        group: cluster.x-k8s.io
        kind: Machine
        version: v1beta1
      metrics: 
        - each: 
            path: 
              - status
              - phase
          help: "machine phase"
          name: phase
```

will lead to following error:

```
E0607 09:12:00.168168  126676 registry_factory.go:469] "kube_cluster_x-k8s_io_v1beta1_Machine_phase" err="[status,phase]: []: strconv.ParseFloat: parsing \"Running\": invalid syntax"
```

This behavior got already addressed to Cluster API community in [issue #6458](https://github.com/kubernetes-sigs/cluster-api/issues/6458#issuecomment-1148293873). The current discussion together with the KSM folks is one in [this slack thread](https://kubernetes.slack.com/archives/CJJ529RUY/p1654593034854759).

With the assumption, that `kube-state-metrics` accept patches which might make CASM obsolete, this section will cover the integration of Cluster API infrastructure provider specific `CustomResourceStateMetrics` configuration.

### Variant 1: specific `kube-state-metrics` configuration for the already existing `kube-state-metrics-app`

As `kube-state-metrics` is already deployed in each cluster (no matter if management- or workload cluster), a condition has to be implemented to detect, if the current KSM instance is running on a management- or a workload cluster. With this condition in place, we can provide a CAPI generic `CustomResourceStateMetrics` configuration plus one `CustomResourceStateMetrics` configuration per infrastructure provider.

#### Pros

- CAPI generic `CustomResourceStateMetrics` configuration could be easily re-used on different providers
- KSM-App already exists

#### Cons

- Scope of KSM between management- and workload cluster differs
  - resource requirements
  - permissions
- Changes in KSM-App affect all clusters, even if changes are only done for management clusters (e.g. version bump)

### Variant 2: dedicated `kube-state-metrics` on management cluster

As `kube-state-metrics` is already deployed in each cluster with a well defined scope, it's also possible to create a dedicated CAPI scoped KSM-App to only monitor Cluster API plus infrastructure specific custom resources.

#### Variant 2.1: dedicated `kube-state-metrics` instance on management cluster for all CAPI providers

One generic KSM instance which bundles all the Cluster API specific `CustomResourceStateMetrics` configuration plus infrastructure specific specific `CustomResourceStateMetrics` configuration.

##### Pros

- Scope of this KSM instance is clearly focused on everything CAPI
- Any further management cluster CR specific monitoring clearly goes there

##### Cons

- Cluster API versions must be reflect in the `CustomResourceStateMetrics` configuration. We will potentially diverge on the used Cluster API versions per infrastructure provider.

#### Variant 2.2: dedicated `kube-state-metrics` instance on management cluster per CAPI providers

Each infrastructure specific installation has an own KSM instance which bundles Cluster API and the infrastructure specific `CustomResourceStateMetrics` configuration.

##### Pros

- As the App is only used by one specific infrastructure implementation, the `CustomResourceStateMetrics` configuration doesn't have to support different Cluster API versions at one time.

##### Cons

- New generic Cluster API specific `CustomResourceStateMetrics` configurations must be adopted/imported into each provider specific repository.

#### Variant 2.3: two dedicated `kube-state-metrics` instances on management cluster per CAPI providers

As the `CustomResourceStateMetrics` configurations mostly correlate with the used Cluster API version and the used infrastructure provider specific version it might make sense to have one KSM for Cluster API and one KSM for the infrastructure provider specific implementation.

#### Pros

- KSM plus the corresponding `CustomResourceStateMetrics` configurations could be bundled in the Apps `cluster-api-app` and `cluster-api-<provider>-app`.
- Additional CRDs, which belong to ClusterAPI or the infrastructure specific implementation could be monitored in via the corresponding `CustomResourceStateMetrics` configurations

#### Cons

- Waste of resources as two additional (small) KSM instances are running per management cluster

## Conclusion

// tbd
