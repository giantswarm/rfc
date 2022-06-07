# Cluster API state metrics

<!-- toc -->
- [Glossary](#glossary)
- [Problem statement](#problem-statement)
- [Cluster API state metrics](#cluster-api-state-metrics)
  - [Infrastructure provider specific metrics](#infrastructure-provider-specific-metrics)
    - [all providers in one binary](#all-providers-in-one-binary)
    - [code separation per provider](#code-separation-per-provider)
    - [Conclusion](#conclusion)
- [Tasks and Stories](#tasks-and-stories)
  - [Story 1](#story-1)
  - [Story 2](#story-2)
  - [Story 3](#story-3)
<!-- /toc -->

This RFC motivates the adoption of the existing Cluster API state metrics project into our own workflow.

## Glossary

- Infrastructure providers - Cluster API infrastructure implementation for e.g. AWS (CAPA), OpenStack (CAPO), Google Compute Platorm (CAPG), ...
- `cluster-api-state-metrics` (CASM)
- `kube-state-metrics` (KSM)
- Management Cluster (MC) is the Kubernetes Cluster where CAPI components are deployed and which is responsible for creating new Kubernetes Clusters (WCs)
- Workload Cluster (WC)

## Problem statement

As Cluster Operator we want to get know the state of any Cluster API related object (no matter if Cluster API Core or infrastructure provider specific).

As different states have impact on the expected behavior of the reconciliation e.g.

- A cluster upgrade won't finish successful if an already existing OpenStackMachine is in an error state (even if the machine is in a transient error).
- It's possible to set nearly all Cluster API related objects into a `paused` state to skip reconciliation for that - primary done by humans.

All these states might lead to different kind of troubleshooting sessions and possibly issues on customer side.

## Cluster API state metrics

As per design `kube-state-metrics` only takes care of Kubernetes resources and all existing Cluster API controllers don't have object related metrics yet, [`cluster-api-state-metrics`](https://github.com/mercedes-benz/cluster-api-state-metrics) was created by Mercedes-Benz.

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

#### all providers in one binary

##### Pros

- Resources can be enabled via an already existing command line flag. Adopting this in a helm-chart becomes quite easy as we already have some provider specific flags on other shared components.

##### Cons

- As different CAPI versions might exist on different kind of MCs we have to ensure that CASM is downwards compatible over multiple providers/teams.
- Transitive dependencies from multiple providers will cause issues.

#### code separation per provider

To separate the code of different providers it's possible to create an own fork per infrastructure provider or setup different main-branches per provider.

##### Pros

- Code ownership is handled per provider, which reflects the separation of our current teams.

##### Cons

- Handling different kind of CASM versions (version means CASM + provider specific implementation) in one App not easily possible.
- Some code maintenance must be done multiple times.

#### Conclusion

As CASM isn't part of Cluster API yet and open questions like how to deal with infrastructure provider are still in discussion with the upstream community, we decided to continue with <PLACEHOLDER - ToDo>

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

As `kube-state-metrics` is already deployed in each cluster, it's also possible to create a dedicated CAPI scoped KSM-App to only monitor Cluster API + infrastructure specific custom resources.

#### Variant 2.1: dedicated `kube-state-metrics` on management cluster for all CAPI providers

##### Pros

- Scope of this KSM instance is clearly focused on everything CAPI
- Any further management cluster CR specific monitoring clearly goes there

##### Cons

#### Variant 2.2: dedicated `kube-state-metrics` on management cluster per CAPI providers

#### Variant 2.3: two dedicated `kube-state-metrics` on management cluster per CAPI providers

-

#### Pros

- KSM

#### Cons

## Tasks and Stories

### Story 1

As a (AWS|OpenStack|GCP|VMWareVCD) platform team i would like to get known the state of relevant Cluster API infrastructure provider specific object, exposed as metric.

### Story 2

As a (AWS|OpenStack|GCP|VMWareVCD) platform team i would like to have alerts on all Cluster API related objects if they are not in a desired state.

### Story 3

CASM should be managed and rolled out via our own App platform.
