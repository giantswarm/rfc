---
creation_date: 2025-01-30
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: TODO
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

With Cluster API on cloud providers we usually have location indicators in cluster resources, in various places. The proposed solution in this RFC would help simplify and unify location lookup for clusters by clients throughout cloud providers.

In on-premises installations, no location information is currently available in Kubernetes resources. This RFC attempts to change that.

The assumption here is that entire clusters are not distributed geographically, so that the entire cluster can be assigned to one geographical location.

### Decision maker

Team Honeybadger with Team Rocket, plus other KaaS teams.

### Deadline

None

### Who is affected / stakeholders

TBD

### Preferred solution

We should set the [`topology.kubernetes.io/region`](https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesioregion) label on the main cluster (currently kind=`Cluster`, group=`cluster.x-k8s.io/v1beta1`) resource of all clusters.

(The label is currently set by Kubernetes on `Node` and `PersistentVolume` resources.)

For clusters running in cloud providers, the value of the label should be the region identifier. E. g. `eu-west-1` for the AWS datacenter in EU/Dublin.

For clusters on premises, the value should follow a system that we establish for this purpose. The system may differ between customers, to allow fulfilling of customer-specific requirements.

Regardless of the environment (cloud/on-prem), the value of the `topology.kubernetes.io/region` label should not include any whitespace and consist of the lowercase letters, numbers, and dash only (`[a-z0-9-]`).

#### On-prem default location ID system

Our default location identification system should be

- easy to use and to understand
- hierarchical
- extensible

Here is a synopsis:

```
<CONTINENT_CODE>-<COUNTRY_CODE>[-<STATE_CODE>][-<CITY_NAME>]
```

Details:

- `CONTINENT_CODE`: The mandatory first part is a two-letter code for the global region/continent. Available are:
  - `af` for Africa
  - `an` for Antarctica (yes, unlikely, but who knows)
  - `as` for Asia
  - `eu` for Europe
  - `na` for North America
  - `oc` for Oceania
  - `sa` for South America
- `COUNTRY_CODE` is the two letter [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code of the country the cluster is located in.
- `STATE_CODE` is the optional code for a subdivision of the country, like it might makes sense for larger countries like the U. S.
- `CITY_NAME` is a concise form of the city name the datacenter is located in.

Depending on the needs for the individual customer, the number of levels in the hierarchy may vary. We should also foresee a change to the naming system after its establishment, e. g. to introduce a state code within one country.

Here are some examples how this system could be applied to identify three different cluster locations:

##### Example 1: Frankfurt am Main, Germany, Europe

- `eu-de-frankfurtmain`
- `eu-de-he-frankfurt` - `he` as the state code for Hessia. In this case, the name "frankfurt" is non-ambigious.

Germany has several cities named "Frankfurt", so without a state code, "frankfurt" alone would be ambigious. Either adding "main" to the city name or adding the state code (`he` for Hessia) solves this.

##### Example 2: Aix-en-Provence, France, Europe

- `eu-fr-aixenprovence`
- `eu-fr-pac-aix` - `pac` as a region code for "Provence-Alpes-Côte d'Azur", which has ISO 3166-2 code `FR-PAC`.

##### Example 3: Dallas, Texas, United States of America

- `na-us-tx-dallas`

##### Optional state and city part

The state code and city name parts are optional and should only be applied if relevant to the customer. In case of a customer that tends to create not more than one data center per country, they could be omitted. Examples:

- `eu-fr` for France
- `af-za` for South Africa
- `sa-br` for Brazil

### Alternative solutions

Have not been explored so far.

### Implementation plan

Not discussed yet.

One major concern is: if a customer creates a new cluster in a new on-prem facility, how is the location identifier determined? Would the customer have to think about this?

### Communication plan

Not discussed yet.
