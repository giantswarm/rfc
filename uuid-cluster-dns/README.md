# Using UUIDs for cluster endpoint domains

> Assumption: this is relevant only going forward with CAPI clusters and not to be "backported" to the vintage product.

## Current Approach

The current approach for building cluster domains is to include the workload cluster's ID as a subdomain of the management cluster it belongs to, e.g.:

```
Workload Cluster: https://api.j9yr2.k8s.gauss.eu-west-1.aws.gigantic.io
Management Cluster: https://dex.g8s.gauss.eu-west-1.aws.gigantic.io
```

The domain contains several parts:

1. The name of the service being accessed (`api`)
2. The workload cluster's ID, which can be user-provided (`j9yr2`) [Workload Cluster only]
3. The static string `k8s` or `g8s`
4. The codename of the management cluster (`gauss`)
5. The region the cluster is deployed into (`eu-west-1`)
6. The cloud provider (`aws`)
7. The static string `gigantic.io`

This approach has a few drawbacks:

1. The workload cluster is tied to the management cluster (belonging to it via domain hierarchy) which is problematic if the cluster needs migrating to another management cluster.
2. Similar to above, workload clusters cannot be "promoted" to management clusters as the domain would no longer make sense.
3. Several customers have their own domain set up, leading to inconsistency between MCs (e.g. `eu-central-1.aws.cps.customer.com` vs. `gauss.eu-west-1.aws.gigantic.io`).
4. The provider (and region) is baked into the domain. While not a major problem today, it does make possibility of multi-region clusters slightly more complex.
5. DNS Hosted Zones are currently set up in different ways between management clusters and workload clusters (Terraform and `dns-operator-[provider]` respectively)

## Existing proposal

An alternative "flat" DNS structure has been proposed that removes the link between workload clusters and management clusters by dropping the management cluster codename from the domain and instead using the customer name (or codename).

E.g.:

```
https://api.j9yr2.k8s.[customer name].eu-west-1.aws.gigantic.io
```

While this solves some of the above drawbacks (1 & 2) it introduces its own complications:

1. The customer name (or codename) is exposed in the domain (not a blocker, but to avoid unintentionally shareing information about our customers we'd need to keep these URLs out of any issues or PR comments etc.)
2. There is no enforced global uniqueness on cluster IDs so if a customer has multiple management clusters there is a chance that two workload clusters have the same ID, leading to conflicting domains. This is especially true when customers set their own cluster IDs.

## Updated Proposal

The flat DNS structure can be improved to avoid the potential conflicts by leveraging a UUID for the cluster domain and dissasociate the cluster ID/Name from URLs.

E.g.

```
https://api.4c6aba87-061c-458d-91b6-62ad07979728.eu-west-1.aws.gigantic.io
```

For this to work we'd need to enforce creation of a new UUID for every cluster on creation.

Cluster names and descriptions can still be used for labels and annotations to provide human-recognisable identifiers when using tools like Happa and kubectl.

This approach is also the same as used by many of the cloud providers for their managed Kubernetes offerings (e.g. EKS).

The benefits of this approach:

* Clusters are no longer permanently associated with a specific management cluster
* The human-friendly cluster name and description are no longer bound to the limitations of DNS. (e.g. Length and valid characters)
* No potentially sensitive information can be leaked from the domain alone (so should be safe to use in GitHub tickets and similar)
* Conflicts in names are avoided by the use of UUIDs, even across customers and providers
* Workload clusters can more easily be "promoted" to management clusters by just installing the required Giant Swarm applications

The drawbacks:
* For customers that require / desire the use of their own domains, some additional setup will be required to ensure the Kubernetes API's certificate is also valid for the customers domain (and then a CNAME can be set up to point to the UUID-based domain)
* The domain name no longer resembles to the human-friendly name of a cluster
* The domain alone doesn't give any indication of which customer it belongs

## Topics that need expanding

* The mechanism for managing the hosted zone delegation is currently unclear
* With a GitOps approach, how would we ensure uniqueness / creation of UUIDs? - A possible solution could be to have a validating webhook prevent creation of clusters with the domain set and a mutating webhook that generates the UUID and sets it. Subsequent updates will need to ensure the domain isn't modified.
