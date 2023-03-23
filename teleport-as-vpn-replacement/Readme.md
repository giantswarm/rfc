# Teleport as a replecement for the currrent VPN solution

## Goals

- Simplify VPN setup
- Simplify access to management and workload clusters for GS employees
- Impove security by having MFC per session 
- Simplify network topology and CIDR allocation 

## Non Goals 
- Use teleport for all  customer access to clusters and services 

## Backgroud

The current vpn solution  

## Immplementation

### Create a central teleport installation

We will start with having a central teleport installation. 
This will be installed on one of our own clusters, i.e the operations cluster using Helm.

### Join tokens and configuration 

We 

### Install teleport agent during KubadmBootstrap on cluster nodes
The teleport agent will be installed on the cluster nodes by providing an installation script and executing it in the pre-kubeadm hook.
example:
```
kind: KubeadmConfig
apiVersion: bootstrap.cluster.x-k8s.io/v1beta1
metadata:
  name: example-config
spec:
  joinConfiguration:
    nodeRegistration:
      kubeletExtraArgs:
        eviction-hard: nodefs.available<0%,nodefs.inodesFree<0%,imagefs.available<0%
  files:
  - contentFrom:
    secret:
      key: teleport-setup
      name: teleport-setup-sh
    owner: root:root
    path: /tmp/install-teleport.sh
    permissions: "0755"
  preKubeadmCommands:
    - /tmp/install-teleport.sh

```
### Install teleport on MC during MC bootstrap
We will install the [helm chart](https://goteleport.com/docs/reference/helm-reference/teleport-kube-agent/) of teleport agent for API access via the app collections.

### Install teleport on WC with default-apps
We will install the [helm chart](https://goteleport.com/docs/reference/helm-reference/teleport-kube-agent/) as a default app.

## Open Questions
- Join token life time and managment
- Can we use AIM for join configuration in the cloud


## Next steps
- Start using teleport for our testing clusters
- Learn more about requirements regarding teleport from our customers
- Roll out teleport to all installations and replace VPN
