---
creation_date: 2023-05-08
state: approved
---

# Default PSS and Policy Exceptions with Kyverno

## Objective

The purpose of this RFC is to communicate Team Shield's plan for moving forward with Kyverno PSS policies as a replacement for PSPs and the associated implications for teams and customers regarding management of policy exceptions.

This RFC will be merged and considered to be accepted on or after 8 May 2023 as soon as no blocker remains (indicated by the "Request changes" PR review option).

## Background

PodSecurityPolicies (PSPs) have been deprecated since Kubernetes v1.21.0. They have been removed as of v1.25.0.

In previous discussions, Shield (and earlier, Ludacris) indicated our intent to replace the PSP functionality with Kyverno policies mapping to Kubernetes Pod Security Standards.

The root issue remains that the official, built-in alternative to PSPs, known as Pod Security Admission (PSA) is not granular enough in its application of policies to suit Giant Swarm or our customers' use cases.
Specifically, only entire namespaces may be targeted for policy enforcement, and that enforcement can only be set to one of three predefined tiers. It is not possible to exempt individual workloads in a namespace from an individual policy.

There are many legitimate reasons to allow for an exception to a policy under various organizational structures and risk appetites.

Given that the underlying motivation for adopting Kyverno PSS is to maintain this granularity of control and exceptions, this RFC outlines the exception mechanism as it will work under Kyverno.

Consensus on the exception mechanism -- at least at a high level -- is important because it will dictate the next steps in the migration towards Kyverno PSS, specifically, the creation of customer-facing guides, product decisions, and supportive tooling.

## Proposal

Shield suggests leveraging the native Kyverno `PolicyException` resource.

A `PolicyException` is a Kyverno custom resource which contains a list of policies and a set of selectors.
Resources matched by the selectors will not be subject to the listed policies (or individual rules listed for a policy containing multiple rules).

The union of all `PolicyExceptions` is evaluated to find any matching exception for an otherwise blocked resource.

Because `PolicyExceptions` are in-cluster resources, they have several advantages:

- access to exceptions can be controlled with Kubernetes-native RBAC
- management of exceptions can be performed through GitOps workflows and eventually backed by other storage, like an OCI registry
- Giant Swarm is able to create very flexible policy exceptions, for example, a sweeping emergency exception from a bad customer policy
- additional optional controls about exceptions can be enforced by Kyverno itself, for example:
  - requiring cryptographic signatures of `PolicyExceptions`
  - limiting the scope of a `PolicyException`, as in these several [examples](https://kyverno.io/policies/other/policy-for-exceptions/policy-for-exceptions/)

Under this model, whenever a resource requires an exception to a configured Kyverno policy, a `PolicyException` can be created by an end user, a security team, a platform team, Giant Swarm, or others, in accordance with cluster RBAC.

This approach is very flexible, so we believe it will be palatable to customers with drastically different security cultures. More detailed examples are included below.

### Giant Swarm Implementation

Each Giant Swarm project currently contains a PSP.
If the application requires permissions not allowed by our security policies, the application's PSP will be directly replaced by one or multiple `PolicyException` resources.
If the application does not require any elevated permissions, it no longer requires any policy resources to be contained in the repository. The PSP will be removed and no replacement will be added.

The first generation of Kyverno PSS-controlled Giant Swarm management clusters will be managed as described in the Developer-Set Exceptions example below. In short: each project deploys its own exceptions in management clusters and workload clusters.

Future improvements to the security platform intend to centralize the exceptions and eliminate the need to maintain individual application-level resources, moving us to a Centralized Exception model.

### Workload Cluster Default Implementation

We currently include a default restricted PSP in each workload cluster. This will be replaced by Kyverno PSS policies, enforced in `restricted` mode.

Customers will have great flexibility in how they deliver `PolicyExceptions` to the cluster for any workloads which are not compliant with the `restricted` standard. Examples of possible exception models are included below.

A newly-created workload cluster will contain `PolicyException` resources deployed for our applications, described above.

### Migration Implications

If this approach is accepted, we expect the migration to involve the following effort from Giant Swarm and our customers.

Giant Swarm:

- creation of `PolicyExceptions` for our applications which require them and can't be made compliant
  - Shield has already made many workloads compliant so they don't require exceptions. Others can still be made compliant.
  - this work could be done in parallel with removal / gating of PSP resources which will need to be removed in post-v1.25 clusters anyway
- (Shield) creation of assistive guides. This is already in progress in parallel, but requires agreement on this RFC to be finalized

Customers:

- creation of `PolicyExceptions` for customer workloads
  - this effort depends significantly on the customer's current model of PSP usage and application behavior
    - for example, we have customers who centrally control all PSPs and customers who allow teams to control their own. Effort for the second is likely to be higher, also from a future management perspective

Shield's experience with early Kyverno adopters is that organizations have drastically different ability and willingness to enforce security policies.
We will provide resources based on what we already know from early adopters, what we learn from Giant Swarm's migration, and the unknown needs that we will inevitably learn from customers as they begin the move.

### Migration Path

More detailed information on the migration path will be published after agreement is reached on this RFC. To help understand the path to PSS adoption, the high-level migration process would be:

1. Kyverno and PSS policies (audit) are added to an upcoming release. This could be a new v19 minor.
    - Result: customers now have information about non-compliant workloads
1. Customers begin creating `PolicyExceptions` for workloads which require them
    - Shield provides docs and support
    - Optionally: customers change individual policies to `enforce` as compliance is achieved
    - Optionally: customers can elect to completely disable PSPs
1. Kubernetes 1.25 release is published, containing policies in `enforce` mode by default
    - Result: PSPs are removed
    - Result: remaining non-compliant workloads will be rejected
    - Result: customers must deploy exceptions for remaining workloads or grant more widely-scoped exceptions (e.g. disabling enforcement of certain policies)

## Alternatives

Multiple alternatives have been considered and attempted over the past two years, including:

### Exceptions via Labels / Annotations

This approach allows resources to opt themselves out of policies by applying certain labels or annotations to the resource.

The advantage of this approach was that it made self-service very easy for developers, and was for some time the only technically feasible way to handle self-service exceptions in Kyverno logic.

There are several major drawbacks, the largest being that labels and annotations are not RBAC-controlled, so this allows most users the ability to exempt themselves from any policy without administrator review.

### Exceptions via Policy

This method captures all exceptions to a policy inside the policy itself. When a new exception is approved, it is added to the Kyverno `Policy` or `ClusterPolicy` resource.

The advantage here was that there was a true single source of truth about the expected policy behavior.

The disadvantage was virtually everything else.
Under this model, only a centralized exception model could be adopted because an administrator would need to add and re-deploy a policy for each new exception. It requires constant modification of and addition to the policy resource, which would eventually hit the etcd resource size limit in complex environments.
It also made it much more difficult to continue using official upstream policies - each policy would need to be copied and heavily modified both by customers and by Giant Swarm.
This would be very error-prone and simply would not scale.

## References

- [Intranet page](https://intranet.giantswarm.io/docs/dev-and-releng/psp-deprecation/) about PSP to Kyverno migration and [corresponding public blog post](https://www.giantswarm.io/blog/giant-swarms-farewell-to-psp)
- [Sample `PolicyException` resource for falco-app](https://github.com/giantswarm/falco-app/blob/main/helm/falco/templates/falco-policy-exception.yaml)
- [Kyverno PolicyException documentation](https://kyverno.io/docs/writing-policies/exceptions/)

## Appendix

### Examples

#### Centralized Exceptions

Most customers prefer to centralize the approval and management of policy exceptions. This has historically included policies of several types, including Pod Security Policies and Network Policies, among others.
These organizations already have established approval processes, in some cases including automated portals where users can request an exception to be automatically deployed to clusters after review by cluster administrators and/or a security team.

Customers operating under this model may prefer to restrict PolicyException creation only to cluster administrators and approved automation.
Exceptions might be stored in a single repository and/or deployed in a single namespace for simplicity.

In the proposed setup, this can be achieved by:

- Not granting the `CREATE polex` permission to non-administrator entities, and
- Using a (Shield-provided) Kyverno Cluster Policy to limit the namespaces where `polex` resources may be created, and
  - Optionally, modifying the policy to allow either:
    - `PolicyException` creation by their approved automation in any namespace
    - `PolicyException` creation by any RBAC-approved entity only in specific namespaces
    - A combination of the above
  - Optionally, deploying additional policies ([examples](https://kyverno.io/policies/other/policy-for-exceptions/policy-for-exceptions/)) to limit the scope of the `PolicyExceptions`

This is the recommended approach for most customers, and is the direction in which Team Shield intends to build future automation to simplify exceptions for Giant Swarm applications.

#### Developer-Set Exceptions

This model is analogous to one where developers already control and deploy their own PSPs.
In this model, cluster administrators permit their internal customers/application developers to declare their own exceptions.
Either the organization does not impose any central control, the control is handled through an earlier approval process (like a code review), or violations are addressed asynchronously after non-compliant resources are audited in the cluster.

In the proposed setup, a customer can enable this model by:

- Granting users the `PolicyException` creation permission in namespaces where they are intended to work, and
- Disabling the Shield-provided Kyverno Cluster Policy to allow `PolicyException` creation in all namespaces, and
  - Optionally, deploying additional policies ([examples](https://kyverno.io/policies/other/policy-for-exceptions/policy-for-exceptions/)) to limit the scope of the `PolicyExceptions` (e.g. so that users can't create an exception with effects beyond their namespace)

#### Hybrid Exception Models

Real-world usage likely won't perfectly resemble either of those models. Because RBAC and policies are heavily customizable by us and by customers, it is possible to create robust alternatives to meet requirements which don't align with either of those models.
However, at this time, we discourage highly bespoke implementations due to the added complexity of managing them.
