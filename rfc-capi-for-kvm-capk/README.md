# RFC: CAPI for KVM (CAPK)

### Use cases

- As a Giant Swarm (GS) Platform Engineer (PE), I want to implement Cluster API (CAPI) for KVM (CAPK) clusters so that I
  don't need to maintain legacy services and libraries (e.g. `k8scloudconfig`, `apiextensions`, `cert-operator`,
  `cluster-service`) for the foreseeable future.
- As a GS PE, I want the operator(s) reconciling KVM clusters (collectively referred to as "KVM operators") to work 
  independently of other GS components so I can add features more quickly and make usage by the wider community more
  feasible/possible.
- As a GS PE, I want KVM operators to work in arbitrary Kubernetes clusters so we can stop maintaining our custom
  provisioning tooling for on-prem management clusters.
- As a GS employee, I want KVM operators to implement the CAPI provider contract so that we can be in the list of
  CAPI providers to improve the reputation of our company.
- As a GS on-premises (on-prem) customer, I want KVM operator to implement CAPI so that I have access to new
  provider-independent features developed by other GS teams.
- As a GS oncall engineer, I want on-prem installations to be as similar as possible to the other providers so that I
  can share best practices, on call routines, and documentation with the other teams.
- As a GS on-prem customer, I want GS to implement a migration strategy from current kvm clusters to CAPI KVM clusters
  so that I can access the new features without service disruption and workload migration.
- As a GS on-prem customer, I want GS to implement a break out/migration strategy for on-prem installations so that I
  can use other CAPI on-prem providers in the future such as CAPV (Cluster API for VSphere (VMWare)) or metal3 (Cluster
  API for bare metal).
- As a member of Team Rocket, I would like to have confidence in my changes to the platform through the use of reliable
  unit, integration, and end-to-end tests.


### Rationale

With the current move to full CAPI adoption in Team Firecracker and Team Celestial, Team Rocket would be the only user
and therefore the only maintainer of the current components and code that would be legacy for the other teams.

This would mean that we would need to put a lot of effort into understanding and owning this code fully in order to be
able to fix bugs and maintain KVM installations
in the future.

Instead of being the sole maintainer of a huge amount of legacy code, Team Rocket wants to invest this time in
implementing CAPI for KVM operator and maintain relative platform parity with the other GS provider teams.

### Goals

- Customers can upgrade existing clusters to CAPK without significant workload downtime.
- Existing CAPI-compatible tools such as kubectl-gs, happa, GS api, and clusterctl work with CAPK clusters.
- Team Rocket is responsible for a significantly reduced number of repos and lines of code.

### Non-goals

- Get CAPK accepted as a CNCF project.
- Support mixed CAPK/CAPV clusters.
- Support mixed management clusters (e.g. CAPK on AWS).
- Support `MachineSet` or `MachinePool`.
- Support CAPI <=v1alpha3.

### Scope

We outlined all existing features in the GS KVM platform to define the scope of the implementation. Many features of
platform can be provided by CAPI now. We therefore split the implementation into features that we must migrate to the
new operator and those we must ensure are handled by CAPI as follows:

#### Features to migrate to new operator

- DNS and NTP configuration for WC nodes (OS level)
- iSCSI initiator name (control plane nodes)
- host volumes (worker nodes)
- etcd storage (host path/persistent)
- cpu and memory limits for control plane and worker node pods and QEMU VMs
- size of kubelet and docker volume
- automatic node termination: using liveness and readiness probes
- drop dead endpoints (don't route traffic to non-ready nodes) using ReadinessGates
- autoscaling for operator pod using VPA

#### Features handled by other controllers

- etcd domain and prefix: using `KubeadmControlPlane`
- docker daemon (mirror, auth, bridge IP, and proxy): using a systemd drop-in unit via `files` in `KubeadmConfig`
- SSH keys for WC nodes: using `KubeadmConfig`
- Calico: using `cluster-apps-operator`
- kube-proxy (conntrack, service IP range): using `KubeadmControlPlane`
- apiserver flags (OIDC): using `KubeadmControlPlane`
- kubelet (clusterDNS, clusterDomain, node labels): using `KubeadmConfig`
- automatic node termination: using `MachineHealthCheck`
- node IP range: will be defined by the MC pod IP range (VMs will use MC Calico network once we finish dropping Flannel)

### Implementation

#### DNS

The WC Kubernetes API is reachable externally (e.g., for GS engineers, customers) via an ingress in the MC of the form
`https://<cluster id>.k8s.<installation base domain>`. This DNS name should resolve to the external IP of the MC ingress
controller.

Inside the WC, control plane nodes should connect to etcd and k8s API via localhost. Workers should use a control plane
endpoint of `https://<cluster id>.k8s.<installation base domain>` or `control-plane.<cluster id>.svc` depending on
whether external DNS or MC CoreDNS is used for WC node DNS resolution (respectively). This will be determined during
implementation.

#### Machine OS Images

The CAPI-native method for OS images is using an image builder to create a different image for each Kubernetes version.
 This implies a lot of complexity and is a big departure from our current approach of configuring nodes using ignition.
 During development, we will use kubeadm `pre-` and `post-` commands to provision nodes. There is upstream activity 
around [image building](https://github.com/kubernetes-sigs/image-builder/blob/master/images/capi/README-flatcar.md) and 
[ignition support in CAPI](https://github.com/kubernetes-sigs/cluster-api/pull/4172) which we will try to stay abreast of.

#### Controller Framework (operatorkit vs kubebuilder)

While we want to avoid too many moving parts, this is a good opportunity to continue aligning more closely with upstream
operators and collaborate with the community by using `kubebuilder`. There are quite a few unknowns around this which we
have summarized below:

##### Features in operatorkit

1. expose `creation_timestamp`, `deletion_timestamp` and `last_reconciled` metrics for every object we reconcile over.
   We use them in the [following](https://github.com/giantswarm/prometheus-rules/blob/8142cac5f47be117ca428fc422d71afd2db3f5ee/helm/prometheus-rules/templates/alerting-rules/operatorkit.rules.yml#L1)
   alerts.
1. create [kubernetes events](https://github.com/giantswarm/operatorkit/blob/master/docs/using_kubernetes_events.md) on
   reconciliation errors
1. sentry client: (**not used in `kvm-operator`**)
1. [pause reconciliation](https://github.com/giantswarm/operatorkit/blob/master/docs/pause_reconciliation.md): do not
   reconcile if there are specific pause annotations (**not used in `kvm-operator`**)
1. setting per controller finalizer (`operatorkit.giantswarm.io/<controller.Name>`)
1. allow deletion events to be [replayed](https://github.com/giantswarm/operatorkit/blob/master/docs/using_finalizers.md#control-flow)
   by setting `finalizerskeptcontext.SetKept(ctx)`
1. when we boot the server we also add two additional endpoints: `healthz` (service availability) and `version`
   (info about the go runtime).

##### Alternatives in kubebuilder

1. Metrics: `kubebuilder` already exposes a few metrics, and we can always add new ones
   ([link](https://book.kubebuilder.io/reference/metrics.html#publishing-additional-metrics)).
1. Events: manager has a `GetEventRecorderFor` method that can be passed to the controller to register events.
1. Finalizers: kubebuilder supports them so we can implement all the stuff we need (pause, replay).
1. Extra endpoints: manager has `AddHealthzCheck` and `AddReadyzCheck` methods that feel similar to the `healthz`
   endpoint.

### Milestones

#### MVP

- Create cluster using manual templates
- Delete cluster
- Scale cluster
- Upgrade cluster
- Pivoting
- Calico CNI via App CR
- Configure Kubernetes version, OS version, and resources for worker and control plane nodes

#### Production-readiness

- Configure docker volume size
- Configure kubelet volume size
- Vertical pod autoscaler for operator pod
- Configure DNS and NTP servers
- Docker network CIDR (this is needed by some customers due to conflicting IP ranges)
- Configure CIDRs for pod and service IPs 

### Appendix A: Full Example Cluster

#### Cluster

```yaml
kind: Cluster
apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
metadata:
  name: example
spec:
  controlPlaneEndpoint:
    host: example.k8s.geckon.gridscale.kvm.gigantic.io
    port: 6443
  infrastructureRef:
    apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
    kind: KVMCluster
    name: example
```

#### KVMCluster

```yaml
kind: KVMCluster
apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
metadata:
  name: example
spec:
  controlPlaneEndpoint:
    host: example.k8s.geckon.gridscale.kvm.gigantic.io
    port: 6443
```

#### KVMachineTemplate (control plane)

```yaml
kind: KVMMachineTemplate
apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
metadata:
  name: example-control-plane
spec:
  template:
    spec:
      resources:
        cpu: 1
        memory: 1Gi
        disk: 20Gi
        dockerVolumeSize: 5Gi
```

#### KubeadmControlPlane

```yaml
apiVersion: controlplane.cluster.x-k8s.io/v1alpha4
kind: KubeadmControlPlane
metadata:
  name: example
spec:
  infrastructureTemplate:
    apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
    kind: KVMMachineTemplate
    name: example-control-plane
  kubeadmConfigSpec:
    initConfiguration:
      nodeRegistration:
        name: '{{ ds.meta_data.hostname }}'
        kubeletExtraArgs:
          cloud-provider: kvm
    clusterConfiguration:
      apiServer:
        extraArgs:
        cloud-provider: kvm
     controllerManager:
      extraArgs:
        cloud-provider: kvm
    users:
    - name: thomas
      sshAuthorizedKeys:
      - ssh-rsa AAA...
    replicas: 1
    version: v1.21.2
```

#### MachineDeployment (worker)

```yaml
apiVersion: cluster.x-k8s.io/v1alpha4
kind: MachineDeployment
metadata:
  name: example-worker
  labels:
    cluster.x-k8s.io/cluster-name: example
spec:
  replicas: 1
  selector:
    matchLabels:
      cluster.x-k8s.io/cluster-name: example
  template:
    metadata:
      labels:
        cluster.x-k8s.io/cluster-name: example
    spec:
      version: v1.21.2
      bootstrap:
        configRef:
          name: example-worker
          apiVersion: bootstrap.cluster.x-k8s.io/v1alpha4
          kind: KubeadmConfigTemplate
      infrastructureRef:
        name: example-worker
        apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
        kind: KVMMachineTemplate
```

#### KVMMachineTemplate (worker)

```yaml
apiVersion: infrastructure.cluster.x-k8s.io/v1alpha4
kind: KVMMachineTemplate
metadata:
  name: example-worker
spec:
  template:
    spec:
      resources:
        cpu: 1
        memory: 1Gi
        disk: 20Gi
        dockerVolumeSize: 5Gi
```

#### KubeadmConfigTemplate (worker)

```yaml
apiVersion: bootstrap.cluster.x-k8s.io/v1alpha4
kind: KubeadmConfigTemplate
metadata:
  name: example-worker
spec:
  template:
    spec:
      joinConfiguration:
        nodeRegistration:
          name: '{{ ds.meta_data.hostname }}'
          kubeletExtraArgs:
            cloud-provider: kvm
      users:
      - name: thomas
        sshAuthorizedKeys:
        - ssh-rsa AAA...
```

#### Release

```yaml
apiVersion: release.giantswarm.io/v1alpha1
kind: Release
metadata:
  name: v20.0.0
spec:
  apps:
  - name: calico
    version: 0.2.0
    componentVersion: 3.18.0
  - name: cert-exporter
    version: 1.6.1
  - name: chart-operator
    version: 2.15.0
  - componentVersion: 1.8.0
    name: coredns
    version: 1.4.1
  - componentVersion: 1.9.7
    name: kube-state-metrics
    version: 1.3.1
  - componentVersion: 0.4.1
    name: metrics-server
    version: 1.3.0
  - name: net-exporter
    version: 1.10.1
  - componentVersion: 1.0.1
    name: node-exporter
    version: 1.7.2
  components:
  - name: cluster-api-bootstrap-kubeadm
    releaseOperatorDeploy: true
    version: 0.4.0-beta.1
  - name: cluster-api-control-plane
    releaseOperatorDeploy: true
    version: 0.4.0-beta.1
  - name: cluster-api-core
    releaseOperatorDeploy: true
    version: 0.4.0-beta.1
  - name: cluster-api-kvm
    releaseOperatorDeploy: true
    version: 0.1.0
  - name: app-operator
    version: 4.4.0
  - name: cluster-apps-operator
    releaseOperatorDeploy: true
    version: 0.1.0
  date: "2021-08-01T12:00:00Z"
  state: active
```

## Appendix B: `clusterctl` provider contract

We would like to support the `clusterctl` provider contract as defined in the
[CAPI book](https://cluster-api.sigs.k8s.io/clusterctl/provider-contract.html). The specifics of this contract are
outlined below.

#### Repository

We will implement a new operator using the
[giantswarm/cluster-api-provider-kvm](https://github.com/giantswarm/cluster-api-provider-kvm/) repository.


#### Variable Names for customization 

##### Infrastructure components configuration

We have nothing to customize in the `infrastructure-components.yaml`.


##### Workload cluster configuration 

Variables in the `cluster-template.yaml`.



| Name | Description | required for provider contract | default |
| -------- | -------- | -------- | -------- |
| ${NAMESPACE}     | The namespace where the workload cluster should be deployed     | Yes     | None |
| ${KUBERNETES_VERSION} | The Kubernetes version to use for the workload cluster  | Yes | None |
| ${CONTROL_PLANE_MACHINE_COUNT} |  The number of control plane machines to be added to the workload cluster | Yes | 3 |
| ${WORKER_MACHINE_COUNT} | The number of worker machines to be added to the workload cluster | Yes | 3 |
| ${CONTROL_PLANE_MACHINE_CPUS}  | The number of CPUs for the control plane VMs | No | 4 |
| ${WORKER_MACHINE_CPUS}  | The number of CPUs for the worker VMs | No | 4 |
| ${CONTROL_PLANE_MACHINE_MEMORY} | The amount of memory for the control plane VMs, for example `8GB` | No | 8GB |
| ${WORKER_MACHINE_MEMORY} | The amount of memory for the worker VMs, for example `8GB` | No | 8GB |
| ${CONTROL_PLANE_DOCKER_VOLUME_SIZE_GB} | The size of the docker disk in GB, for example `40` | No | 40 |
| ${CONTROL_PLANE_VOLUME_SIZE_GB} | The size of the VMs disk in GB, for example `40` | No | 40 |
| ${DOCKER_VOLUME_SIZE_GB} | The size of the docker disk in GB, for example `40` | No | 40 |
| ${VOLUME_SIZE_GB} | The size of the VMs disk in GB, for example `40` | No | 40 |
| ${POD_IP_RANGE} | IP range for the Workload Cluster Pods | No | 172.24.0.0/16|
| ${SERVICE_IP_RANGE} | IP range for the Workload Cluster Services | No | 172.31.0.0/16 |


#### Labels 

We will label all our CRDS with `cluster.x-k8s.io/provider=infrastructure-kvm`

#### CI/CD

We need a solution for attaching `infrastructure-components.yaml` and `cluster-template.yaml` files to CAPK GitHub
releases. We can build this automation ourselves using GitHub actions or reuse what other infrastructure providers use.


## Appendix C: Deprecated components

Many components are already deprecated or in the process of being deprecated for AWS and Azure. Below is a list of these
components and the general plan for migrating away from them or integrating them into maintained components.

Operators:
- `kvm-operator` Updated for CAPI or replaced with new operator
- `node-operator`: Integrated into `kvm-operator`
- `cluster-operator`: Some logic integrated into `kvm-operator`, apps manged by `cluster-apps-operator` (CAPI-only)
- `flannel-operator`: Not needed without flannel
- `cert-operator`: Replaced by `cert-manager`

Services:
- `api`: Replaced by CAPI/MAPI
- `cluster-service`: Replaced by CAPI/MAPI
- `kubernetesd`: Replaced by CAPI/MAPI
- `bridge-operator`: Not needed without flannel
- `flannel-network-health`: Not needed without flannel
- `k8s-network-bridge`: Not needed without flannel
- `k8s-api-healthz`: Deprecated
- `k8s-kvm`: Replaced by `containervmm`
- `k8s-endpoint-updater`: Deprecated

Libraries:
- `k8scloudconfig`: Integrated into `kvm-operator` and replaced by CAPBK
- `operatorkit`: Possibly deprecated
- `exporterkit`: Possibly deprecated
- `apiextensions`: Split into operator repos
- `badnodedetector`: Possibly integrated into `kvm-operator`
- `microstorage`: Deprecated
- `certs`: No longer needed without `cert-operator`
- `versionbundle`: Deprecated
- `statusresource`: Replaced by CAPI
- `randomkeys`: Maybe deprecated in `cluster-operator`

Tools:
- `gsctl`: Replaced by `kubectl-gs` and `clusterctl`
