# Teleport as a replecement for the currrent VPN solution

## Goals

- Simplify VPN setup
- Simplify access to management and workload clusters for GS employees
- Impove security by having MFC per session 
- Simplify network topology and CIDR allocation 
- Eliminate need for per provider bastion host conifguration and implementation
- Get rid off bastion hosts
- Allow access to private clusters where we currently can't have access
- Manage all infrastructure required for cluster access with k8s itself, no need for additional VMs.

## Non Goals 
- Use teleport for all  customer access to clusters and services 

## Backgroud

The current vpn solution is having some limitations. 
- CIDR management: we currently need a uniqe CIDR per customer which are sometimes hard to find due to overlapping CIDRs in the customers environment
- No single sign on and MFC: vpn access is issued per user and can be revoked quickly, but we don't have a single sign on and MFA
- VPN servers, users and Bastion hosts need to be managed
- No easy ssh session audit logging for now

## Immplementation

### Create a central teleport installation

We will start with having a central teleport installation. 
This will be installed on one of our own clusters, i.e the operations cluster using Helm.

### Join tokens and configuration 

Suggestion is to start with one long lived token per installation.
Things we need to learn:
- What happens during node reboot if a join token has expired or has been rotated? <!-- TODO -->
- Can we use AIM or similar in the cloud. <!-- TODO -->

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
We will install the [helm chart](https://goteleport.com/docs/reference/helm-reference/teleport-kube-agent/) of teleport agent for API access via the app collections. We label the clusters as with  for better searchability  as documented [here](https://github.com/gravitational/teleport/tree/branch/v12/examples/chart/teleport-kube-agent#kubernetes-access). <!-- TODO come up with a labeling shema -->  
Example: `labels.installation=guppy labels.customer=giantswarm labels.environment=testing labels.mc=true labels.wc=false`

### Install teleport on WC with default-apps
We will install the [helm chart](https://goteleport.com/docs/reference/helm-reference/teleport-kube-agent/) as a default app. and use the same labels as for the managment clsuters, except that we set `labels.mc=false, labels.wc=true`

## Open Questions
- Join token life time and managment
- Can we use AIM for join configuration in the cloud
- Cluser / Node labeling schema in teleport


## Next steps
- Start using teleport for our testing clusters
- Learn more about requirements regarding teleport from our customers
- Roll out teleport to all installations and replace VPN
- Leaf teleport proxy server per installation for mor data separation and scalability
