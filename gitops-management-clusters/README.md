# RFC 0002 - Enable customers to use gitops in management clusters

We currently give customers access to the management clusters but do not support them in utilizing this access effectively in terms of git ops related management (e.g. for apps).

Context:
Some customers might be interested in utilizing mainstream git ops tooling in order to manage their apps across clusters and installations.

## Open Questions

### 1. General direction
1.1 We would like to allow our customers to choose their management tooling freely. Do we want to support some tools with e.g. a managed app first though?

1.2 Do we own the gitops tooling or is it purely owned by the customer?

### 2. Technical issues
2.1 How does the setup for an in-cluster agent look like? Currently customers will struggle setting up an in-cluster agent with appropriate permissions.

2.2 How do we ensure security requirements when customer interaction increases?

2.3 Do we foresee issues when introducing gitops tooling to already existing resources?

### 3. Guidance
3.1 How do we support customers in making sensible decision in terms of tooling choice with gitops?

3.2 Do we aid customers with repository structure for their gitops approach?

3.3 Do we offer customers to give us shared access to their repository for additional review?
