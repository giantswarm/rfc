# Sharing Kyverno Policies with Customers

This mini-RFC documents the result of [a discussion](https://github.com/giantswarm/giantswarm/issues/26365) about Kyverno policies we deploy in customer clusters.

The outcome of this RFC should be to clarify the general expectation of Kyverno policies in workload clusters, and optionally to generate additional discussions for the points that remain unclear.

## TL;DR

We used a Kyverno policy to implement some behavior, and didn't anticipate that customers might also use the policy. When we changed the policy for our usage, it broke the functionality for the customer.

Since we will give customers lots of Kyverno policies for Pod Security Standards (PSS) in the future, we should let them assume that policies we deploy are intended for their usage.

If that isn't true for a certain policy, the responsibility is on us to make that clear and reduce the likelihood that customers will use it mistakenly.

## Context

To support running a cluster behind a proxy, we created a Kyverno mutating policy which injects environment variables containing proxy details into Pod resources at admission time.
Pods are mutated by this policy only if they have a certain label.

A customer noticed this capability, and began using the label to have their pods also mutated to include the proxy information.

We did not realize that the customer had begun using it, and modified the policy in a way that made it no longer work for the customer.

The resulting discussion is about what expectations we and customers can have about the stability of Kyverno policies in workload clusters.

## Discussion Points

In the resulting issue and subsequent sync, the following questions arose:

1. Is a Kyverno policy the correct place to implement this logic to begin with? Is this a permanent solution or is there an alternative to be implemented in the long term? --> Out of scope of this RFC.
1. What is the expectation of the proxy support in our product? Do we provide a mechanism for customer workloads, or must customers configure their own workloads to use the proxy? --> Out of the scope of this RFC.
1. To what extent are Kyverno policies part of our public interface to customers? --> Focus of this RFC.

The first two questions are about the specific policy in question and are worth separate discussions, but not in this RFC, which hopes to address the general case of Kyverno policies in WCs.

## Current State

We deploy several types of Kyverno policies to management (MC) and/or workload clusters (WC):

- Pod Security Standards (PSS) policies --> MC + WC
- UX policies (e.g. block deletion of Orgs which still have clusters) --> MC
- DX policies (e.g. limit Crossplane or External Secrets management) --> MC
- Observability policies (e.g. ServiceMonitor defaulting) --> MC (+ WC?)
- Connectivity policy for proxy --> MC + WC

With the move to Kyverno PSS, we set a huge precedent for customers relying on policies provided by Giant Swarm.

We (particularly Shield) also anticipate adding more WC Kyverno policies for things like best practices and for supporting other platform capabilities.

The proxy policy is the first we've deployed to WCs which wasn't intended to apply to customer workloads.

## Proposal

Kyverno policies deployed in workload clusters should be generally assumed to be applicable to customer workloads.

If this is not the case for a particular policy, the owners of the policy should:

- make it clear in the policy description that the policy applies only to Giant Swarm resources
- craft the policy in a way that customers can not opt themselves into it unexpectedly
- consider using RBAC or adding a supplemental policy controlling the use of the main policy

If those have been done, we consider our intent clear, and will not provide any guarantee of the stability of that policy for customer usage.

## Rationale

In a Kyverno PSS world, customers will quickly become accustomed to using policies we provide.

Kyverno policies will be evaluated for every API server request. We should avoid applying logic to every API request unless it is serving a purpose for that traffic.

Consider two other components we manage in customer clusters: node-exporter and coredns.

Node-exporter is deployed by default so that we can monitor node health. We do not provide an interface for a customer to modify its behavior, but we do not prevent them from scraping it if they choose. We deploy node-exporter for our own purposes, and could theoretically choose to replace it with minimal customer impact. Customers may (and some do) choose to deploy an additional copy of node-exporter if they wish to customize its behavior. Similarly, customers can simply deploy their own copy of our Kyverno policy if they want to use it as-is.

Coredns is also deployed by default. DNS is a cluster-wide concern, but we provide an interface to configure it (via the Corefile, configured through our App Platform). If we were to replace it with a different implementation, we'd expect that change to have customer impact. However, it is not expected that a customer runs a parallel installation of Coredns if they wish to customize it. As a policy analogy, we would not configure routes in the cluster-wide DNS configuration which were only for use by Giant Swarm applications.

There is some product incongruity between those two apps -- they are both managed apps, but somehow conceptually different.

The question is, are Kyverno policies more like node-exporter or Coredns?

The API server is our customer interface, and Kyverno policies will inspect every interaction. Given that Kyverno policies define the behavior of a cluster-wide admission controller, if we deploy policies in a workload cluster, there is a reasonable expectation that they are generally applicable to the objects going through admission in that cluster.

So, in other words, if a policy we manage is not applicable to customers or to the cluster generally, then we should take steps to constrain the policy behavior and make it clear that it isn't part of our intended interface.
