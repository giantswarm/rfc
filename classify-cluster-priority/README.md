# Classifying clusters based on priority

Contents:

1. User stories
2. Current practice
3. Proposal
4. Considerations and explanations
5. Possible applications

## User stories

- As a cluster admin, I want to easily communicate the purpose and importance of a cluster to those interacting with it, so that they can act accordingly.
- As Giant Swarm operations staff I want to understand the importance of clusters so I can make appropriate decisions, e. g. when prioritizing problem mitigation in an incident affecting multiple clusters.

## Current practice

- One customer uses the first character of the cluster name to distinguish between production (`p`), development (`d`), and staging (`s`). This customer also has clusters which don't fall into either of these categories and their names start with arbitrary letters.
- Many customers use specific terms and phrases in the cluster description, e. g. "Production", "test", "testing", "ignore alerts", "prd", "prod", "nonprod".
- Some customers use labels on the `clusters.cluster.x-k8s.io` resource (the cluster's main resource) indicating the importance, e.g:
    - `odp/environment: development`
    - `odp/environment: staging`
    - `odp/environment: production`.

## Proposal

We introduce a label and a schema for the label values to indicate the relative importance of a cluster.

Label name: `giantswarm.io/service-priority`

The label is to be used on the main resource defining the cluster, usually of resource type `clusters.cluster.x-k8s.io`.

To simplify maintenance and avoid logical conflicts, this label SHOULD NOT be applied on other resources of the cluster. Systems MUST ignore the label used on other resources in the same cluster. This means that it is not possible, for example, to differentiate between the importance of several node pools within the same cluster.

### Well-defined label values

There are three well-defined label values to be used.

- `giantswarm.io/service-priority: critical`: This is the highest priority class. Clusters with this label value are considered the most important ones, relative to other clusters not carrying this label. We expect customers to use this class for clusters serving user-facing applications, production traffic, etc.

- `giantswarm.io/service-priority: important`: Clusters carrying this label are considered less important than `critical`, but still more important than clusters classified as `unimportant`. Typical use cases would be staging clusters, clusters handling batch workloads, or development clusters that cannot be replaced easily by creating a new cluster.

- `giantswarm.io/service-priority: unimportant`: The lowest priority class. Customers are expected to use this class for clusters that isn't relied on, or which can be replaced easily and quickly.

### Absence of the label

The absence of the label SHOULD be interpreted as if the label was present with the value `critical`.

### Using undefined values

If the label is used with a value different from the well-defined ones, the label SHOULD be interpreted as if the value was `development`.

## Additional considerations and explanations

- Understanding of this system by Giant Swarm staff is crucial. We have to make sure that everybody in operations know about the system.

- Individual customers may or may not use the system. It is not required that all customers adopt it for it to become usable.

- Customers that already have a classification scheme implemented should be encouraged to also implement the system proposed here. Several systems can co-exist side by side, however in that case Giant Swarm staff will be instructed to consider the system described here as the authoritative one.

- The label, by default, has no effect on monitoring, alerting, support, usage cost, routing priority, workload quality of service (QoS) etc. of the cluster. However it MAY serve as an input for such automation in the future.

- The `kubectl gs template cluster` command SHOULD be extended to include the proposed label, with the default value being `critical` and the other well-defined labels to be set via flags. This will help give the system more visibility and increase adoption.

- While it is possible to set labels on clusters via the Management API or in cluster manifests, it is also recommendable to extend the web UI to set the proposed label and choose a well-defined value on cluster creation.

- While it is already possible to set, modify, and delete cluster labels via the web UI, it is also recommended to make it simpler for end users to specify the proposed label with a well-defined value for a given cluster.

## Possible applications

To help interpreting the proposal and judge its significance, here we suggest some applications that would make use of the described labelling system. This does not mean that we must implement any of these when approving this RFC.

- In the web UI there are several places where the proposed label can be displayed as useful information for users:

    - In the cluster list, as an indicator especially for clusters classified as `critical` and `important`.

    - On the cluster details page.

    - When deleting a cluster, especially in case the cluster is classified as `critical` and `important`, to highlight the purpose of the cluster.

- In kubectl-gs, when listing clusters using the `get clusters` command, an additional column `SERVICE PRIORITY` can be added to display the value based on the label (or the default value `critical`, in case of absence).

- We could add the label to our monitoring, to include the priority information as a criterium in visualization or alerting.

- We may provide or suggest automation to customers to silence alerts based on the labelling scheme.
