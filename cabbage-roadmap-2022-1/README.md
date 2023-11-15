---
creation_date: 2022-04-07
state: approved
---

# Team Cabbage Roadmap 2022

This RFC describes the roadmap for Team Cabbage for the first part of 2022.

## Background

Since the formation of Team Cabbage just after the Croatia onsite (~September 2021), up to the start of 2022, Team Cabbage's overall focus has been on getting started as a team.

This involved the usual work for team formation, including defining Jobs To Be Done and overall mission statement. We had a number of issues to clean up or sort out, such as dissolving Team Halo, postmortems, and app upgrades. We also updated the monitoring and alerting for our apps.

Finally, we continued improving our support for shipping Kong as a Managed App, and shipped the AWS LB Controller as a Managed App.

## Jobs To Be Done

The Jobs To Be Done for Team Cabbage can be summarised as follows:

- Exposing services running on a Kubernetes cluster
- Routing, observing, and securing traffic into, inside, and out of Kubernetes clusters
- Managing API services on Kubernetes clusters

These describe the tasks that users want to do, and help frame the problem space the team works in.

There is a lot of overlap between these jobs, and it is important to remember that we want to provide one story to customers - i.e: providing a turn-key traffic solution for Fortune 500 customers.

## Discovery

Before moving to the more concrete opportunities, it's useful to cover more long-term patterns and use cases we're thinking about. These are items that are not yet ready for us to tackle, but are going to form the basis for our product discovery over the new few months, and will likely form part of our roadmap in the future.

We also need to make sure that we take the current strategic move to Cluster API into account.

### Gateway API

See the [upstream project](https://gateway-api.sigs.k8s.io/).

Gateway API can be described as a possible future replacement for the current [Ingress API object](https://kubernetes.io/docs/concepts/services-networking/ingress/), aiming to provide a more well-rounded API for describing service networking in Kubernetes.

We need to firm up our strategy with Ingress generally, and more specifically our plans with the Ingress NGINX Controller.

Given upstream direction, it is likely that we will need to provide a managed Gateway API solution. We also have concerns about the maintainership of Ingress NGINX Controller - there is currently a lack of support for Gateway API, and no clear plans for adding that support.

There are alternative solutions we're considering offering, such as Contour / Envoy, Kong, or Traefik, among others. These support Gateway API, and appear to be better maintained.

We may begin with offering these solutions as opt-in. We may also decide to fully replace our current Ingress solution with one of these projects - it would be better for this to happen proactively, as replacing all our managed Ingress Controllers is a large engineering task.

We believe Gateway API can help support better multi-tenancy, and improve separation of concerns, within the use case of exposing services. We want to research further what use cases Gateway API can satisfy, as well as the performance of solutions.

### Multi Cluster Services

See the [upstream KEP](https://github.com/kubernetes/enhancements/tree/master/keps/sig-multicluster/1645-multi-cluster-services-api).

Services spanning across multiple clusters has been discussed with some of our more advanced users. One use case discussed is how can users run their services over two clusters in different zones, and still serve traffic in the face of one zone going down.

There is some discussion on whether this solution would come in the form of service meshes, or whether it would require a more involved global load balancing solution.

We want to investigate what technology we can get from upstream, as well as work more with our advanced users on their use cases.

### Alternative CNIs

CNI as a topic is currently owned by the Kubernetes-As-A-Service teams. However, as Team Cabbage covers a number of connectivity stories, it may make sense to consider how Team Cabbage could be resposible for CNI, and provide alternative CNI solutions, such as Cilium.

Alternative CNIs also possibly become easier with the move to Cluster API, as CNI is less 'baked-in' than with the current Giant Swarm Kubernetes product.

### Alternative API Gateways

We currently offer Kong as our only fully managed API gateway solution. However, we should be aware of other API gateways entering the market, in case a more appropriate solution becomes available.

The increase in use of Gateway API may also lead to more offerings in this space.

## Opportunities

These are our more concrete opportunities for product development. That is, product ideas we have identified that we could start working on in the near-term, and would provide some amount of customer value.

### Extending our user base of Kong

We currently have Kong in production with one customer, and are proceeding with getting Kong into production with another customer.

The overall aim is to keep and make both customers very satisfied with our Kong offering, and possibly see if we can find and close Kong with another customer. We can continue to improve our support of Kong, such as by improving the Helm chart and our monitoring and alerting. We can also help these customers move to Kong Enterprise for additional features.

We also want to improve our partnership with Kong Inc., and see how we can work together in the future.

The effort is not particularly high here, as we are already in production with Kong, and the customer value is quite high.

### Getting Linkerd into production

We consider Linkerd a key component in our overall connectivity offering, but do not use it ourselves on our Management Clusters. We also do not have it in production with any customers yet, although at least one customer has shown strong interest in using Linkerd.

We can work on improving our Linkerd offering, by improving the Helm chart and our monitoring and alerting. We can deploy Linkerd to our own Management Clusters. We can also work with our advanced users to get them using Linkerd in production.

The effort here is higher than with Kong, but we do already have a workable offering. The customer value is quite high.

### Scaling Ingress NGINX Controller on custom metrics

We currently offer horizontal pod autoscaling for Ingress NGINX Controller based on the CPU and memory usage of the Ingress NGINX Controller Pods. CPU and memory are not the best metrics to scale on - the number of requests currently being served would be more suitable. We could build support in our Ingress NGINX Controller offering to scale on these custom metrics.

We have some customers with extremely bursty traffic patterns, meaning they need to pre-scale their clusters before high load events. We would likely not be able to enable them to scale on demand, even with the ability to scale on custom metrics.

The effort for this is somewhat middling, but so is the customer impact.

### External monitoring of Ingress Controllers

We currently monitor Ingress Controllers from the monitoring systems deployed on the Management Cluster. This can be problematic in situations where the Ingress Controllers are seen as available to our monitoring systems, but are not available to the Internet as a whole, such as with some forms of network failure.

We could provide an monitoring service that tests whether Ingress Controllers are accessible from the Internet.

The effort here is middling, and customer impact would be somewhat middling as well.

### octavia-ingress-controller

The [Octavia Ingress Controller](https://github.com/kubernetes/cloud-provider-openstack/tree/master/docs/octavia-ingress-controller) allows for better load balancer integration on OpenStack. Similarly to the AWS LB Controller, it allows for users to configure Octavia load balancers to point directly to their services.

We could provide the octavia-ingress-controller as a Managed App. This should be fairly straightforwards, but does require some involvement with OpenStack networking. The customer impact would probably be quite low, considering the smaller number of OpenStack installations currently, due to it being a new provider.

### Network Policies for all services in Management Clusters

We currently do not run our Management Clusters with a 'deny all' network policy - i.e: we do not deny all traffic by default, and rely on services to explicitly define which services they need to talk to.

We can move to denying all network traffic on our Management Clusters by default, and add Network Policies for all services that require them.

The effort here is fairly low (and all of the work is internal to Giant Swarm), but customer impact is fairly low too.

Given our move to re-using Workload Clusters as Management Clusters in the future, it would be fairly straightforward to keep the default 'deny all' network policy used by Workload Clusters, and require teams to add Network Policies to ensure their services work with the new style of Management Cluster. This would keep the overall work for Team Cabbage to a minimum.

### Moving to upstream charts

We currently use our own Helm charts for some components owned by Team Cabbage, notably Ingress NGINX Controller and external-dns. We could move to use upstream charts for these components. This would reduce time and effort required to keep them up to date.

The effort could be fairly high here with Ingress NGINX Controller as it is a critical component, and there would be minimal customer impact.

## Roadmap

Given the above, our plan for the start of 2022 is:
- to continue working on our Kong offering, get both customers we're currently working with to the latest version of Kong, and get them using Kong Enterprise
- to deploy Linkerd to our Management Clusters
- to get Linkerd into production with one customer

Bam! <3
