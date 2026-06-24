---
creation_date: 2025-01-30
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: The document discusses the need for consistent location metadata for clusters, addressing customer communication and management needs. It proposes a unified location identifier metadata system on the cluster level, for cloud and on-premises clusters.
---

# Location metadata for clusters

### Problem statement

For some of our customers, the physical location of an installation and its clusters is an important differentiator. They communicate in terms like these (paraphrased):

- the Dublin management cluster
- the dev cluster in Singapore
- the China installation

Some on-prem customers use location identifiers like city names in cluster descriptions.

Relevant user stories in this context could be, to name two examples:

- As a platform admin, I want to check the Kubernetes version of all clusters in a certain location.
- As a service owner, I want to check the deployment status of certain apps in a certain location.

So location information is relevant for customers and Giant Swarm engineers alike. However, currently the location information is not consistently available in Kubernetes resources nor user interfaces.

With Cluster API on cloud providers we usually have location indicators in cluster resources, in various places. Each cloud provider uses their own identifier system, however they all make use of a string identifier. The proposed solution in this RFC would help simplify and unify location lookup for clusters by clients throughout cloud providers.

In on-premises installations, no location information is currently available in Kubernetes resources. In metrics (Prometheus/Mimir) and logs (Loki) we annotate many series with a `region` label. However, in on-prem installations, the value for this label is always `onprem`. This RFC attempts to change that.

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

- Setting consistent metadata on Cluster API cluster resources
- Providing a customizable location ID system for on-prem customers
- Setting the `region` label in metrics accordingly

#### The location label

We introduce a label `TOPIC.giantswarm.io/location`, to be set on any cluster. The label's value is a string that identifies the location of the cluster. We consider it optional, but recommended.

TODO: Specify the `TOPIC` for the label group.

In the Kubernetes project, the well-known label [`topology.kubernetes.io/region`](https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesioregion) is documented and (as of February 2025) is used on `Node` and `PersistentVolume` resources, but not expected on Cluster resources. Its values is usually the region identifier of the cloud provider the node/volume is running in (example: `eu-west-1` for the AWS region in EU/Dublin). For clusters, there is no such label yet.

For on-premises clusters, the value should follow a system that we establish for this purpose. The system may differ between customers, to allow fulfilling of customer-specific requirements.

Note: The purpose of the location label value is _not_ to provide universally understandable location information. Instead, the purpose is simply to tag clusters with specific locations. For better human understanding, a lookup table may be maintained per customer, which also should affect the display of location information in user interfaces like Backstage.

#### Default location ID system for on-prem

The label described above requires to specify the location of a cluster as a single string.

For our on-premises customers, we want to provide a default system to inidicate their cluster's locations. This default system should be

- easy to use and to understand
- hierarchical
- adaptable/customizable

It should be up to the customer to decide if they want to deviate from the system and populate the label mentioned above with whatever string they like. For example, let's just assume a customer has a numeric system to enumerate their facilities. In that case, they should be able to use that identifier instead of our default system.

For our default system, here is a synopsis of the format:

```
<CONTINENT_CODE>-<COUNTRY_CODE>[-<SUBDIVISION_CODE>[-<CITY_NAME>]][-<NUMBER>]
```

Each code should avoid any whitespace and consist of the lowercase letters, numbers, and dash only (`[a-z0-9-]`).

This means that the location ID string is composed of two to five components, separated by a dash. The first two parts, the continent code and the country code, are mandatory. If a location has to be specified more precisely, a state code can be added. Furthermore a city name may be added for hightest precision. Lastly, a number may be used to indicate a specific facility at a location with several facilities.

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

#### Setting the region label in metrics

Currently the `region` label for on-premises installations always has the value `onprem`. In cloud installations, the label is set to the cloud region identifier.

For both cloud and on-premises installations/clusters, we want the `region` label of metrics to be set according to the `topology.kubernetes.io/region` label of the cluster. For metrics regarding an application, the region label should represent the cluster the application is deployed to.

For example, given a management cluster named `example-mc` in region `eu-de-hamburg` has an App resource to deploy an app in workload cluster `example-wc` that is located in region `eu-fr-pac-aix`, the application's metrics (if having a region label at all) should be labelled with `region="eu-fr-pac-aix"`.

### Alternative solutions

- We consdidered applying the well-known label `topology.kubernetes.io/region` to cluster resources.
  However, since the system behind the labelling is Giant Swarm specific to a certain degree, we decided to highlight that fact by introducing a new label with our own namespace.

- Instead of strings, we could introduce a system that provides geo coordinates. (Since the cloud providers already work with string identifiers, this draft opts for a solution that extends this paradigm to on-prem.)

### Implementation plan

Team Honeybadger would assemble the default hierarchy, at least up to the second level (country), and partly up to the third level (subdivision code). We don't need global coverage with level three initially, as we can still extend our code table once new customers are onboarded or more locations are needed. The maintained code table should be applied as part of the cluster creation form(s), for quick location selection/entry.

The observability side (metrics labelling) would have to be implemented separately by Team Atlas.

The cluster-app may be extended, so that the values schema provides a dedicated field for the location label, similar to the service priority label. Defaulting based on the management cluster location might worth considering, to keep the cluster creation user experience simple.

### Communication plan

When onboarding new on-prem customers, we should ask them about their desired cluster locations. This way we can make sure to provide the required location codes to select from in cluster creation UIs.

We shoulds also inform on-prem customers proactively about the significance of the location metadata and its application in user interfaces like Backstage.

### Terminology

- KaaS: Kubernetes as a service

## Appendix

### Default location ID codes for on-prem

Below is a preview of the default ID code system for on-prem, to the country level. This is for preview purposes only and won't be maintained here in this RFC.

| Code | Country |
| --- | --- |
| `af-ao` | Angola |
| `af-bf` | Burkina Faso |
| `af-bi` | Burundi |
| `af-bj` | Benin |
| `af-bw` | Botswana |
| `af-cd` | Democratic Republic of the Congo |
| `af-cf` | Central African Republic |
| `af-cg` | Congo |
| `af-ci` | Ivory Coast |
| `af-cm` | Cameroon |
| `af-cv` | Cape Verde |
| `af-dj` | Djibouti |
| `af-dz` | Algeria |
| `af-eg` | Egypt |
| `af-er` | Eritrea |
| `af-et` | Ethiopia |
| `af-ga` | Gabon |
| `af-gh` | Ghana |
| `af-gm` | Gambia |
| `af-gn` | Guinea |
| `af-gq` | Equatorial Guinea |
| `af-gw` | Guinea-Bissau |
| `af-ke` | Kenya |
| `af-km` | Comoros |
| `af-lr` | Liberia |
| `af-ls` | Lesotho |
| `af-ly` | Libya |
| `af-ma` | Morocco |
| `af-mg` | Madagascar |
| `af-ml` | Mali |
| `af-mr` | Mauritania |
| `af-mu` | Mauritius |
| `af-mw` | Malawi |
| `af-mz` | Mozambique |
| `af-na` | Namibia |
| `af-sz` | Eswatini |
| `af-td` | Chad |
| `an-aq` | Antarctica |
| `an-bv` | Bouvet Island |
| `an-gs` | South Georgia and the South Sandwich Islands |
| `an-hm` | Heard Island and McDonald Islands |
| `an-tf` | French Southern Territories |
| `as-ae` | United Arab Emirates |
| `as-af` | Afghanistan |
| `as-am` | Armenia |
| `as-az` | Azerbaijan |
| `as-bd` | Bangladesh |
| `as-bh` | Bahrain |
| `as-bn` | Brunei |
| `as-bt` | Bhutan |
| `as-cn` | China |
| `as-cy` | Cyprus |
| `as-ge` | Georgia |
| `as-id` | Indonesia |
| `as-il` | Israel |
| `as-in` | India |
| `as-iq` | Iraq |
| `as-ir` | Iran |
| `as-jo` | Jordan |
| `as-jp` | Japan |
| `as-kg` | Kyrgyzstan |
| `as-kh` | Cambodia |
| `as-kp` | North Korea |
| `as-kr` | South Korea |
| `as-kw` | Kuwait |
| `as-kz` | Kazakhstan |
| `as-la` | Laos |
| `as-lb` | Lebanon |
| `as-lk` | Sri Lanka |
| `as-mm` | Myanmar |
| `as-mn` | Mongolia |
| `as-mv` | Maldives |
| `as-my` | Malaysia |
| `as-np` | Nepal |
| `as-om` | Oman |
| `as-ph` | Philippines |
| `as-pk` | Pakistan |
| `as-ps` | Palestine |
| `as-qa` | Qatar |
| `as-sa` | Saudi Arabia |
| `as-sg` | Singapore |
| `as-sy` | Syria |
| `as-th` | Thailand |
| `as-tj` | Tajikistan |
| `as-tl` | Timor-Leste |
| `as-tm` | Turkmenistan |
| `as-tr` | Turkey |
| `as-tw` | Taiwan |
| `as-uz` | Uzbekistan |
| `as-vn` | Vietnam |
| `as-ye` | Yemen |
| `eu-ad` | Andorra |
| `eu-al` | Albania |
| `eu-at` | Austria |
| `eu-ba` | Bosnia and Herzegovina |
| `eu-be` | Belgium |
| `eu-bg` | Bulgaria |
| `eu-by` | Belarus |
| `eu-ch` | Switzerland |
| `eu-cy` | Cyprus |
| `eu-cz` | Czech Republic |
| `eu-de` | Germany |
| `eu-dk` | Denmark |
| `eu-ee` | Estonia |
| `eu-es` | Spain |
| `eu-fi` | Finland |
| `eu-fr` | France |
| `eu-gb` | United Kingdom |
| `eu-gr` | Greece |
| `eu-hr` | Croatia |
| `eu-hu` | Hungary |
| `eu-ie` | Ireland |
| `eu-is` | Iceland |
| `eu-it` | Italy |
| `eu-li` | Liechtenstein |
| `eu-lt` | Lithuania |
| `eu-lu` | Luxembourg |
| `eu-lv` | Latvia |
| `eu-mc` | Monaco |
| `eu-md` | Moldova |
| `eu-me` | Montenegro |
| `eu-mk` | North Macedonia |
| `eu-mt` | Malta |
| `eu-nl` | Netherlands |
| `eu-no` | Norway |
| `eu-pl` | Poland |
| `eu-pt` | Portugal |
| `eu-ro` | Romania |
| `eu-rs` | Serbia |
| `eu-ru` | Russia |
| `eu-se` | Sweden |
| `eu-si` | Slovenia |
| `eu-sk` | Slovakia |
| `eu-sm` | San Marino |
| `eu-ua` | Ukraine |
| `eu-va` | Vatican City |
| `na-ag` | Antigua and Barbuda |
| `na-bb` | Barbados |
| `na-bs` | Bahamas |
| `na-bz` | Belize |
| `na-ca` | Canada |
| `na-cr` | Costa Rica |
| `na-cu` | Cuba |
| `na-dm` | Dominica |
| `na-do` | Dominican Republic |
| `na-gd` | Grenada |
| `na-gt` | Guatemala |
| `na-hn` | Honduras |
| `na-ht` | Haiti |
| `na-jm` | Jamaica |
| `na-kn` | Saint Kitts and Nevis |
| `na-lc` | Saint Lucia |
| `na-mx` | Mexico |
| `na-ni` | Nicaragua |
| `na-pa` | Panama |
| `na-sv` | El Salvador |
| `na-tt` | Trinidad and Tobago |
| `na-us` | United States |
| `na-vc` | Saint Vincent and the Grenadines |
| `oc-as` | American Samoa |
| `oc-au` | Australia |
| `oc-ck` | Cook Islands |
| `oc-fj` | Fiji |
| `oc-fm` | Micronesia |
| `oc-gu` | Guam |
| `oc-ki` | Kiribati |
| `oc-mh` | Marshall Islands |
| `oc-mp` | Northern Mariana Islands |
| `oc-nc` | New Caledonia |
| `oc-nf` | Norfolk Island |
| `oc-nr` | Nauru |
| `oc-nu` | Niue |
| `oc-nz` | New Zealand |
| `oc-pf` | French Polynesia |
| `oc-pg` | Papua New Guinea |
| `oc-pw` | Palau |
| `oc-sb` | Solomon Islands |
| `oc-tk` | Tokelau |
| `oc-to` | Tonga |
| `oc-tv` | Tuvalu |
| `oc-vu` | Vanuatu |
| `oc-wf` | Wallis and Futuna |
| `oc-ws` | Samoa |
| `sa-ar` | Argentina |
| `sa-bo` | Bolivia |
| `sa-br` | Brazil |
| `sa-cl` | Chile |
| `sa-co` | Colombia |
| `sa-ec` | Ecuador |
| `sa-gy` | Guyana |
| `sa-pe` | Peru |
| `sa-py` | Paraguay |
| `sa-sr` | Suriname |
| `sa-uy` | Uruguay |
| `sa-ve` | Venezuela |
