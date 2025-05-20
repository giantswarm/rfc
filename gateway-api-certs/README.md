---
creation_date: 2025-05-20
issues:
- https://github.com/giantswarm/roadmap/issues/3150
owners:
- https://github.com/orgs/giantswarm/teams/team-cabbage
state: review
summary: |
    This RFC describes the Gateway API certificates issues.
---

# Title
<!-- Provide a concise and descriptive title for the RFC. -->
Managing Certificates in Gateway API

### Problem statement
Gateway API manages certificates at the Gateway level, requiring the secret to be explicitly defined in the Listener block. This contrasts with Ingress, where secrets are defined at the Ingress (route) level and dynamically picked up by the ingress controller.

#### Certificate generation
Cert-manager remains the preferred solution for certificate generation. This can be initiated through two methods.

- Annotation:
To automate Certificate CR creation, cert-manager can watch the Gateway CR. When a hostname is defined in a Gateway's Listeners, cert-manager will automatically generate the corresponding Certificate CR.

Users need permission to edit Gateway custom resources and add new hosts, keeping in mind that each Gateway can support a maximum of 64 listeners.

Attaching wildcard domains and certificates to a Gateway is an option, but our customers often prefer not to do this.

- Certificate CR:
Users can create a Certificate CR and ReferenceGrant concurrently with an HTTPRoute. However, the secret must still be defined within the Gateway CR.

#### Customer needs
Customers want to avoid updating the Gateway CR for every new hostname. Additionally, the transition from a single Ingress resource to multiple resources is perceived as a potential complication.

### Decision maker
- Team Cabbage
- SIG Architecture

### Preferred solution
TBD

### Alternative solutions
TBD

### Implementation plan
TBD

### Communication plan
TBD




### Problem statement
<!-- Explain the issue or challenge that needs to be addressed. This should include background information and context to help stakeholders understand why this decision is important. -->
Adoption of a Gateway API implementation and replacing Ingress requires of architactural decisions and stablishing different ways of handling the different componets.
