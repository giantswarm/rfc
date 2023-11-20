---
creation_date: 2023-10-12
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/chapter-architecture
state: approved
summary: Switch to Azure Container Registry (ACR), even for China. Instead of replicating images across our multiple registries, trust this single provider to solve high availability. Run a local pull-through proxy to fall back during provider outage.
---

# Leaving docker hub and simplifying registries architecture

## Intro

We decided to leave docker hub by the end of 2023, as their pricing policy and negotiation style is no longer acceptable
to us.

Additionally, our current registry setup is quite complex. We use multiple registries (quay, docker hub, Azure Container
Registry [ACR]) for container images. We use different backends for container images and for helm charts. As a result,
we have to run synchronization tools to move stuff and replicate across our different registries. For more info and
diagrams showing how the current solution works, please see
[here](https://handbook.giantswarm.io/docs/product/architecture-specs-adrs/specs/registry-mirror/#how-are-images-synchronised-between-registries).

While switching away from Docker Hub, we would like also to simplify the architecture, which now involves multiple registries and caring for replication across them. The main reason we started to use replicated registries was
a requirement of one of our former customers. While this has some benefits in terms of reliability, it also brings
complexity and cost of running
the synchronization software on our side. We want to offload the problem of High Availability to a registry provider and
not to handle it ourselves. To protect us from potential service provider down time or networking issues, we will run a
local pull-through proxy. This solution should also limit the cost of the remote registry a lot.

One important implication of the proposed change is how it affects our customers. Since now we use the paid subscription
for Docker Hub, we log in all the container runtimes on all the nodes using our docker hub credentials. This makes
customers use our subscription to download any images from docker hub: ones that are needed to run our infrastructure,
as well as any other. After switching to a new architecture, we will care for availability of our images, but leave
customer's images in the default configuration. This means, that they can start hitting rate limiting where previously
nothing like that happened. It also means that they might want to configure their own registries in the container
runtimes to work around this issue.

Using this approach, we will be able to simplify our architecture, limit the cost (Docker Hub is expensive and gets worse)
and keep HA properties of our infrastructure.

### Specific problems and goals to solve

More specifically, our aim is to:

- Stop using Docker Hub by the end of 2023.
- Simplify registries architecture.
- Switch entirely to OCI based registries for both container images and helm charts.
  - Flux developers have already declared that no new feature will come to Flux for users of HTTP-based repos, only for OCI.
  - Currently, we use a mix of HTTP and OCI repos, but chart discovery uses HTTP-based ones only.
- If possible, switch to single OCI provider.
- Increase availability and lower the network transfer cost by providing a pull-through cache service.
- Automatically clean old dev release artifacts.
- If possible, use the registry provider to replicate registries between Europe and China.
- Use a solution, that works natively with `containerd` and `helm` and doesn't need tricks like mutating webhooks,
  that change Pod's image.

### Implementation stages

In order to keep the scope of this doc full, but to better organize the discussion and to make implementation
divisible into more granular steps, we split the full new architecture into separate stages:

1. Switching docker hub to ACR - [described](#switching-container-images-registry) in this document.
1. Adding a caching solution - [cache.md](cache.md).
1. Switching app platform to OCI only - [app-platform-oci.md](app-platform-oci.md).
1. Switching China from Aliyun to ACR - [china.md](china.md).

### Proposed solution architecture

The target architecture would look like below (dashed lines for pull actions mean fall-back registries):

![Registries architecture diagram](./2023-10-registries.drawio.svg "Registries architecture")

Please note, that instead of a per-MC cache instance, we might want to run just one cache per cloud provider's region.
Check the discussion [below](#open-questions).

## Switching container images registry

### Choosing OCI repository provider

We checked for the single best registry and chose ACR. We did some evaluation before and you can read results here:

- <https://github.com/giantswarm/roadmap/issues/2382>
- <https://hackmd.io/gqF6PT53RcG_i4OhrmtWIw#Note-on-compatibility>

Additionally, ACR offers the following:

- High availability by definition.
- Automatic geo-replication, including geo-replication between Europe and China (confirmed by Azure support, requires
  going through a formal process, though).
- Automatic retention
  - When enabled, manifests that don't have any associated tags (untagged manifests) and are not locked, will be
    automatically deleted after the number of retention days specified. [Docs](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-retention-policy).
- Best-in-class support for the OCI standard (it's MS that is pushing it forward).
- Reasonable pricing
  - price per region €1.540/day (500 GB included), then €0.003/GB/day + traffic fee
  - [Azure cost calculator](https://azure.microsoft.com/en-us/pricing/calculator/?service=container-registry)

## Implementation notes

Very short and brief implementation idea. We can plan more details once we agree on the idea and solution.
We want to start with the images registry, as that's what we currently use Docker Hub for.

### Container images

Currently, we use two ACR registries, `giantswarm` for container images and `giantswarmpublic` for helm charts.
The images one is already over 4 TB in size and it will be hard to clean it up. We can instead start with a new
empty repo and populate it using a separate instance of `retagger`. We won't start uploading build artifacts there
before we figure out how to use the retention policy.

High level migration plan:

- bootstrap a new ACR registry for images, let's call it tentatively `gsoci`
  - configure access, geo-replication (if needed) and a retention policy for the repo
- for our images: switch our CI/CD pipelines to not tag dev build artifacts
  - use a tool (`skopeo`, `retagger`?) to replicate all (do we really need all?) the tagged versions of images we build from the old `giantswarm` repo to the new `gsoci`
  - configure CI/CD (architect) so it uploads to both the old `giantswarm` and the new `gsoci`
- deploy a new instance of `retagger` that will replicate all the configured public images to the new `gsoci` registry
- switch container runtimes to use the `gsoci` registry
- cleanup (after some time)
  - delete our registries in docker hub and quay
  - delete the old `giantswarm` registry in ACR
- for this part, we keep China registry unchanged
  - we keep the current build process to upload to China directly during the build or reconfigure the `crsync`
     to replicate images from `gsoci` to `aliyun` in China

## Open questions

Before we start on the implementation, we have to figure out answers to questions below:

1. How to not tag dev builds?

   ACR has a neat new feature that allows for automatic cleanup of untagged artifacts after a certain period. Currently,
   we upload a ton of dev build images. This feature allows us to clean them up automatically, with zero effort on
   the cleaning process on our side. Still, we have to switch our CI/CD configs to not tag dev builds in any way. What's
   the best way to do it?

1. Customers will stop using our Docker Hub subscription.

   Most customers aren't probably even aware of this, but right now all the images the nodes of any cluster pull from
   Docker Hub, they do so using our Docker Hub subscription. After implementing this change, we wil stop doing this.
   Moreover, we will ensure unlimited downloads only for images that we manually picked and uploaded (using `retagger`)
   to our new ACR registry. We have to explain and announce this change to our customers. Also, we probably have to
   accept that some customers might want us to configure `containerd` to use their Docker Hub credentials to avoid
   rate limiting. How do we do that?

1. How to reconfigure existing and future nodes to use ACR as the registry for our images?

   We have to reconfigure existing MCs and WCs, but also future ones. We have to track and check all the configuration
   sources. Is this even possible for vintage WC releases?

1. How to cleanup existing registries?

   Currently, we use 4 different registries and we more or less upload everything everywhere. We have to figure out
   how to clean them up and leave only artifacts that can be potentially used (a proposition is already discussed
   [above](#implementation-notes))

## References

- [registry mirrors](https://handbook.giantswarm.io/docs/product/architecture-specs-adrs/specs/registry-mirror/)
- [OCI spec](https://github.com/opencontainers/distribution-spec)
- [Azure registry proxies in China](https://github.com/Azure/container-service-for-azure-china/blob/master/aks/README.md#2-container-registry)
