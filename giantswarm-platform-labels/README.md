---
creation_date: 2025-02-25
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/sig-architecture
state: review
summary: This RFC proposes a new label to identify pods by their platform subsystem, aiming to simplify operations and maintenance. The label will use free-form text values, with a documented list of common values. Implementation includes adding the label to a repository and documentation.
---

# Title
Standardizing Platform Component Labeling

### Problem statement
<!-- Explain the issue or challenge that needs to be addressed. This should include background information and context to help stakeholders understand why this decision is important. -->
Currently, platform components are not labeled to indicate their belonging to specific subsystems. This lack of a standardized subsystem label creates some operational challenges.

Firstly, subsystems composed of multiple applications lack a unified identifier. While individual applications are labeled, targeting an entire subsystem requires listing each application's specific label, leading to cumbersome and error-prone configurations. For example, network policies for DNS traffic must explicitly target both coredns and k8s-dns-node-cache, exposing the implementation details to customers.

Secondly, changes in the underlying implementation of subsystems requires widespread label updates. When the prometheus-agent was migrated to alloy, the labels used for metric and log scraping had to be updated across various tools and documentation, requiring a transitional period where both old and new labels were maintained. This introduces unnecessary complexity and maintenance overhead.

The absence of a generic subsystem label hinders our ability to target pods in a flexible and maintainable manner in NetworkPolicies or other operational tooling. This lack of abstraction exposes implementation details, increases maintenance burden, and complicates operational tasks. We have identified at least two key use cases where this issue is prominent: DNS traffic management and metric/log scraping during implementation changes. This issue impacts multiple applications and subsystems, highlighting the need for a standardized approach to subsystem labeling.

### Decision maker
<!-- Identify the person (preferred) or a group responsible for making the final decision. -->
SIG-Architecture

### Who is affected / stakeholders
<!-- List the individuals, teams, or SIGs that will be impacted by this decision and must provide feedback. -->

### Preferred solution
<!-- Describe the solution that is currently favored based on the analysis of the problem. -->

This RFC proposes introducing a label, `platform.giantswarm.io/subsystem`, to identify pods belonging to specific platform subsystems. This label will enable us to target groups of pods based on their subsystem affiliation, simplifying operations and improving maintainability.

Example Usage:

To label pods belonging to the "dns" subsystem, the label would be applied as follows: `platform.giantswarm.io/subsystem: dns`.

Label Values:

The `platform.giantswarm.io/subsystem` label will utilize free-form text values. However, a documented list of currently used subsystem values will be maintained to ensure consistency and provide guidance. This list will be updated as new subsystems are introduced or existing ones evolve.

Documentation:

Documentation on the purpose, usage, and values of the subsystem label will be added to the **Kubernetes resource annotation reference** documentation page and to the [k8smetadata package](https://github.com/giantswarm/k8smetadata/).

### Alternative solutions
<!-- Outline other potential solutions that were considered. For each alternative, provide a brief description and explain why it was not chosen as the preferred solution. -->
Some alternative label names are available that, to some extent, represent the goal of this document.

- giantswarm.io/component
- giantswarm.io/feature
- giantswarm.io/characteristic

Upstream labels have also been suggested, in particular [app.kubernetes.io/part-of](https://kubernetes.io/docs/reference/labels-annotations-taints/#app-kubernetes-io-part-of).

### Implementation plan
<!-- Detail the steps required to implement the preferred solution. This should include a timeline, resources needed, and any dependencies or risks associated with the implementation. -->

1. Add label to github.com/giantswarm/k8smetadata
2. Document label in docs.giantswarm.io
3. Implement label where desired

### Communication plan
<!-- Describe how the decision and its implementation will be communicated to stakeholders. -->
