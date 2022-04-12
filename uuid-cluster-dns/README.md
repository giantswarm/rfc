# Using UUIDs for cluster endpoint domains

The current approach for building cluster domains is to include the workload cluster's ID as a subdomain of the management cluster it belongs to, e.g.:

```
https://api.j9yr2.k8s.gauss.eu-west-1.aws.gigantic.io
```

This approach has a few drawbacks:

1. The workload cluster is tied to the management cluster, making migration messy
2. Workload clusters cannot be "promoted" to management clusters as the domain would no longer make sense
3. Several customers have their own domain set up, leading to inconsistency between MCs (e.g. `eu-central-1.aws.cps.customer.com` vs. `gauss.eu-west-1.aws.gigantic.io`)
4. The provider (and region) is baked into the domain, effectively preventing multi-region (or multi-cloud)

An alternative "flat" DNS structure has been proposed that removes the link between WC and MC. E.g.:

```
https://api.j9yr2.k8s.[customer name].gigantic.io
```

While this solves some of the above drawbacks (1, 2, 4) it introduces its own complications:

1. The customer name (or codename) is exposed in the domain
2. There is no enforced global uniqueness on cluster IDs so if a customer has multiple MCs there is a chance that two workload clusters have the same ID, leading to conflicting domains

## Proposal

> Assumption: this is relevant only going forward with CAPI clusters and not to be "backported" to the vintage product.

The flat DNS structure can be improved to avoid the drawbacks above my leveraging a UUID for the cluster domain and dissasociate the cluster ID/Name from URLs.

E.g.

```
https://api.4c6aba87-061c-458d-91b6-62ad07979728.k8s.gigantic.io
```

For this to work, we'd need to generate a new UUID for a cluster either when running `kubectl-gs template cluster` (for use cases where GitOps are used) or via some defaulting logic when clusters CRs are applied.

Cluster names and descriptions can still be used for labels and annotations to provide human-recognisable identifiers when using tools like Happa and kubectl.

This approach is also the same as used by many of the cloud providers for their managed Kubernetes offerings (e.g. EKS).

The benefits of this approach:

* Clusters are no longer associated with a specific management cluster
* Clusters can be "renamed" (e.g. a cluster that was previously a dev enviroment being promoted to production) and moved (e.g. between cloud provider regions) without changes needed to the domain
* Infrastructure / environment details are no longer needed/exposed in the domain
* No potentially sensitive information can be leaked from the domain alone (so should be safe to use in GitHub tickets and similar)
* Conflicts in names are avoided by the use of UUIDs, even across customers and providers
* Workload clusters can more easily be "promoted" to management clusters by just installing the required Giant Swarm applications.

For customers that require the use of their own domains, some additional setup will be required to ensure the Kubernetes API's certificate is also valid for the customers domain (and then a CNAME can be set up to point to the UUID-based domain).

## Topics that need expanding

* It's currently unclear how and where hosted zones will be created.
* Our tooling (kubectl-gs, happa, etc.) will need to be updated to better surface information that may be lost in this approach (such as the region a cluster is deployed to).
* With a GitOps approach, how would we ensure uniqueness of UUIDs?
