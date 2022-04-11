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

The flat DNS structure can be improved to avoid the drawbacks above my leveraging a UUID for the cluster ID rather than a user-providable short string.

E.g.

```
https://api.4c6aba87-061c-458d-91b6-62ad07979728.k8s.gigantic.io
```

For this to work, we'd need to remove the ability for user-provided cluster IDs and encourage the use of descriptions instead. If cluster names are still desired we could introduce the concept similar to how the description is (label or annotation).

This approach is also the same as used by many of the cloud providers for their managed Kubernetes offerings.

The benefits of this approach:

* Clusters are no longer tied to a specific management cluster
* Clusters can be "renamed" and moved without changes needed to the domain
* Infrastructure / environment details are no longer needed in the domain
* No potentially sensitive information can be leaked from the domain alone (so should be safe to use in GitHub tickets and similar)
* Conflicts in names are avoided by the use of UUIDs, even across customers and providers

For customers that require the use of their own domains, some additional setup will be required to ensure the Kubernetes API's certificate is also valid for the customers domain (and then a CNAME can be set up to point to the UUID-based domain).
