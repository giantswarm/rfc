---
creation_date: 2025-XX-XX
issues:
- https://github.com/giantswarm/roadmap/issues/3150
owners:
- https://github.com/orgs/giantswarm/teams/team-cabbage
state: review
summary: |
    TBD
---

# Title
<!-- Provide a concise and descriptive title for the RFC. -->
Resource migration from Ingress to Gateway API

### Problem statement
<!-- Explain the issue or challenge that needs to be addressed. This should include background information and context to help stakeholders understand why this decision is important. -->
Migrating from Ingress to Gateway API is a significant change that requires careful consideration of the features and compatibility between implementations.

#### Feature parity
Not all features covered by Ingress implementations are available in the Gateway API specification. This means that those missing features must be translated to Gateway API implementation-specific custom resources.

#### Ecosystem
Adoption of the Gateway API has not been consistent across the traffic management ecosystem, and there is a significant disparity in the maturity level of supporting tooling.

#### Mantenance and change management
As the features and tools mature, the need for specific CRs that cover certain features can change.

### Decision maker
<!-- Identify the person (preferred) or a group responsible for making the final decision. -->
Team Cabbage
SIG Architecture

### Preferred solution
<!-- Describe the solution that is currently favored based on the analysis of the problem. -->
As a first option, we propose developing a kubectl-gs template subcommand that receives an Ingress as input and outputs an HTTPRoute plus all the other CRs needed to cover the Ingress features.

This option has the advantage that we can include all the CRs we consider necessary, e.g., Envoy Gateway CRs, Certificates, DNSEndpoints, all based on the annotations the original Ingress had, solving both feature parity problems and the ecosystem maturity issue.

The main disadvantage is that this solution moves the maintenance burden to the customers, as they will need to keep the CRs up to date with the latest features and changes in the Gateway API specification.

### Alternative solutions
<!-- Outline other potential solutions that were considered. For each alternative, provide a brief description and explain why it was not chosen as the preferred solution. -->

The main alternative we considered was creating an operator that handles all the extra resources around the Gateway API CRs. This operator would be responsible for creating and maintaining the extra resources needed to cover the Ingress features.

There are two options for implementing this operator:

1. Keeping the original annotations of the Ingress in the HTTPRoute and creating the extra CRs based on those annotations.
2. Creating a companion CRD that users would use to specify the features and create the extra CRs based on that.

### Implementation plan
<!-- Detail the steps required to implement the preferred solution. This should include a timeline, resources needed, and any dependencies or risks associated with the implementation. -->

TBD

### Communication plan
<!-- Describe how the decision and its implementation will be communicated to stakeholders. -->

TBD
