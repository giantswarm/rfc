---
creation_date: 2025-XX-XX
issues:
- https://github.com/giantswarm/roadmap/issues/3150
owners:
- https://github.com/orgs/giantswarm/teams/team-cabbage
state: review
summary: The RFC addresses the challenges of migrating from the current Ingress-based traffic management to the more modern Gateway API.
---

# Title
<!-- Provide a concise and descriptive title for the RFC. -->
Resource migration from Ingress to Gateway API

### Problem statement
<!-- Explain the issue or challenge that needs to be addressed. This should include background information and context to help stakeholders understand why this decision is important. -->
Our customers rely on Ingress for managing external access to their Kubernetes clusters. While Ingress has served well, the Gateway API offers a more expressive, extensible, and role-oriented approach to traffic management. However, migrating from Ingress to Gateway API presents several key challenges that require careful consideration.
This document is focused on three elements related to the actual translation between Ingress resources and Gateway API resources.

#### Feature parity
The Gateway API, while promising, does not yet cover the entire feature set available in various Ingress controller implementations. Addressing this gap involves translating these missing features (annotations) into implementation-specific Custom Resource (CRs) for our chosen Gateway API controller.

#### Ecosystem maturity
The ecosystem surrounding the Gateway API is still evolving. Tools like cert-manager or external-dns are still in the early stages of adoption of the new API and support is not mature.

#### Maintenance and change management
As the Gateway API specification matures and the capabilities evolve, the specific CRDs and configurations required to achieve feature parity with our current Ingress setup are also likely to change.


### Decision maker
<!-- Identify the person (preferred) or a group responsible for making the final decision. -->
Team Cabbage
SIG Architecture

### Preferred solution
<!-- Describe the solution that is currently favored based on the analysis of the problem. -->
Our initial approach to address the challenges of migrating from Ingress to Gateway API is to develop a kubectl-gs template subcommand. This tool would take an existing Ingress resource as input and generate a set of Gateway API resources, primarily an HTTPRoute, along with any necessary supplementary Custom Resource (CRs) required to replicate the functionality defined in the original Ingress.

The key advantage of this strategy is that it provides us with a high degree of control over how Ingress features are translated into the Gateway API ecosystem. By directly generating the required CRs, including those specific to our chosen Gateway API implementation (e.g., Envoy Gateway CRs), as well as related resources like Certificates and DNSEndpoints, based on the annotations present in the original Ingress, we can effectively bridge the feature parity gap and address the current variability in ecosystem maturity.

However, a consideration is that this approach places the maintenance of these generated resources with our customers. They will be responsible for updating the generated manifests to incorporate new Gateway API features, adapt to specification changes, and potentially manage the lifecycle of the supplementary CRs.

### Alternative solutions
<!-- Outline other potential solutions that were considered. For each alternative, provide a brief description and explain why it was not chosen as the preferred solution. -->

The main alternative we considered was to create an operator that manages the additional resources required by our implementation. This operator would be responsible for the creation and maintenance of the supplementary resources necessary to achieve feature parity with Ingress.

There are two potential implementation options for this operator:

1. An operator that observes HTTPRoute resources and creates the necessary extra CRs based on annotations present in the HTTPRoute.
2. An operator that watches a new, companion CR defined by us, which users would use to specify the desired features, and then creates the corresponding extra CRs based on the specifications in this custom resource.

### Implementation plan
<!-- Detail the steps required to implement the preferred solution. This should include a timeline, resources needed, and any dependencies or risks associated with the implementation. -->

TBD

### Communication plan
<!-- Describe how the decision and its implementation will be communicated to stakeholders. -->

TBD
