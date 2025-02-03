---
creation_date: 2025-01-30
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: To indicate where in a world a cluster is location
---

# Location metadata for clusters

### Problem statement

We have anecdotal evidence that customers think about our installations in terms of their physical location. They communicate in terms like these (paraphrased):

- the Dublin management cluster
- the dev cluster in Singapore
- the China installation

Some on-prem customers use location identifiers like city names in cluster descriptions.

Relevant user stories in this context could be, to name two examples:

- As a platform admin, I want to check the Kubernetes version of all clusters in a certain location.
- As a service owner, I want to check the deployment status of certain apps in a certain location.

With Cluster API on cloud providers we usually have location indicators in cluster resources, in various places. Each cloud provider uses their own identifier system, however they all make use of a string identifier. The proposed solution in this RFC would help simplify and unify location lookup for clusters by clients throughout cloud providers.

In on-premises installations, no location information is currently available in Kubernetes resources. This RFC attempts to change that.

### Key assumptions

This RFC assumes that each cluster exists in one location only, and nodes of the same cluster are not distributed geographically.

### Decision maker

- Team Honeybadger as driver
- KaaS teams, especially Rocket

### Deadline

None

### Who is affected / stakeholders

- Customers
- Giant Swarm engineers

### Preferred solution

The solution proposed here consists of two parts:

- Setting consistent metadata on clusters
- Providing a default location ID system for on-prem customers

#### Consistent metadata on clusters

We should set the [`topology.kubernetes.io/region`](https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesioregion) label on the main cluster resource of all clusters. Currently (as of February 2025) this resource is of kind `Cluster`, group=`cluster.x-k8s.io/v1beta1`.

The `topology.kubernetes.io/region` label is documented as w well-known label, set by Kubernetes on `Node` and `PersistentVolume` resources.

For clusters running in cloud providers, the value of the label should be the region identifier. E. g. `eu-west-1` for the AWS region in EU/Dublin.

For clusters on premises, the value should follow a system that we establish for this purpose. The system may differ between customers, to allow fulfilling of customer-specific requirements.

Regardless of the environment (cloud/on-prem), the value of the `topology.kubernetes.io/region` label should not include any whitespace and consist of the lowercase letters, numbers, and dash only (`[a-z0-9-]`).

#### Default location ID system for on-prem

The metadata system described above allows to specify the location of a cluster as a single string.

For our on-premises customers, we want to provide a default system to inidicate their cluster's locations. This default system should be

- easy to use and to understand
- hierarchical
- adaptable/customizable

It should be up to the customer to decide if they want to deviate from the system and populate the label mentioned above with whatever string they like. For example, let's just assume a customer has a numeric system to enumerate their facilities. In that case, they should be able to use that identifier instead of our default system.

For our default system, here is a synopsis of the format:

```
<CONTINENT_CODE>-<COUNTRY_CODE>[-<SUBDIVISION_CODE>[-<CITY_NAME>]]
```

This means that the location ID string is composed of two to four components, separated by a dash. The first two parts, the continent code and the country code, are mandatory. If a location has to be specified more precisely, a state code can be added, and lastly a city could can be added for hightest precision.

Depending on the customer's needs, a cluster in Frankfurt am Main, Germany, could bear either of the following three location identifiers:

- Country-level precision: `eu-de`
- Country subdivision level precision: `eu-de-he`
- City level precision: `eu-de-he-frankfurt`

Component details:

- `CONTINENT_CODE`: The mandatory first part is a two-letter code for the global region/continent. Available are:
  - `af` for Africa
  - `an` for Antarctica (yes, unlikely, but who knows)
  - `as` for Asia
  - `eu` for Europe
  - `na` for North America
  - `oc` for Oceania
  - `sa` for South America
- `COUNTRY_CODE` is the two letter [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code of the country the cluster is located in.
- `SUBDIVISION_CODE` is the code for a subdivision of the country, like it might makes sense for larger countries like the U. S. If CITY_NAME is specified, the SUBDIVISION_CODE must be given.
- `CITY_NAME` is a concise form of the city name the cluster is hosted in, also optional.

### Alternative solutions

- Instead of `topology.kubernetes.io/region`, we could specify our own label in the `giantswarm.io` namespace. The latter would make sense in case we wanted to mark that there would be some logical difference between these labels.

- Instead of strings, we could introduce a system that provides geo coordinates. (Since the cloud providers already work with string identifiers, this draft opts for a solution that extends this paradigm to on-prem.)

### Implementation plan

Team Honeybadger would assemble the default hierarchy, at least up to the second level (country), and partly up to the third level (subdivision code). We don't need global coverage with level three initially, as we can still extend our code table once new customers are onboarded or more locations are needed. The maintained code table should be applied as part of the cluster creation form(s), for quick location selection/entry.

The cluster-app may be extended, so that the values schema provides a dedicated field for the location label, similar to the service priority label.

### Communication plan

When onboarding new on-prem customers, we should ask them about their desired cluster locations. This way we can make sure to provide the required location codes to select from in cluster creation UIs.

We shoulds also inform on-prem customers proactively about the significance of the location metadata and its application in user interfaces like Backstage.

### Terminology

- KaaS: Kubernetes as a service
