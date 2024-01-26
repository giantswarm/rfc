# Caching solution for OCI

## Intro

Please refer to <README.md>.

## Choosing caching solution

There are at least a few solutions possible, below is a list of solutions evaluated:

- <https://goharbor.io>
  - Seems very complex to run, just [the list of needed components](https://goharbor.io/docs/2.2.0/install-config/) scares
    me off. We want a simple cache, not all the bells and whistles with a ton of components we have to keep running.
- <https://github.com/enix/kube-image-keeper>
  - seems to support container images only, works by a webhook rewriting pod's image - doesn't meet assumptions.
- <https://gitlab.cronce.io/foss/oci-registry>
  - OCI compliant, works with `containerd` by registering as a mirror, no webhooks, optional S3 storage - seems
    like exactly what we need.
  - Tested it, but I unfortunately [couldn't make it work](https://github.com/mcronce/oci-registry/issues/14) even for a simple test case, doesn't seem to be well supported.
- [ACR connected registry](https://learn.microsoft.com/en-us/azure/container-registry/intro-connected-registry)
        - there's no mention of how to deploy outside of AKS edge cluster, seems Azure IoT edge thing only
- [docker's distribution/distribution](https://github.com/distribution/distribution)
  - one instance can proxy only for a single upstream registry (but that's OK for us)
  - tested, works with `containerd` for single upstream repo, works as well with `helm` charts
  - no extra dependencies, can work with just local filesystem storage
  - exposes reasonable prometheus metrics (transfer times, cache hit ratio)
  - <https://distribution.github.io/distribution/about/configuration/>
  - <https://docs.docker.com/docker-hub/mirror/>
- [zot](https://github.com/project-zot)
  - full standalone OCI registry that directly implements OCI standards
  - reviewed when in `v2.0.0-rc6`, while majority of docs are valid for `v1.4.3`
  - has some really nice options, including caching as an optional extension
    - ability to scan images with `trivy`
    - multiple upstream repos to track
    - on-demand (pull-through) and in advance image caching
    - single binary with no dependencies
    - supports local and S3 storage
      - S3 is required for "cluster mode": running more than 1 Pod
    - monitoring with prometheus
    - hard to configure, as docs for v2.0.0 are not there yet
    - it seams there's no cache prune configuration for the cache (potential show-stopper)
    - has a simple "status" web UI
    - had to be configured with auth even for public repos (weird, potential bug)
    - definitely needs more attention/evaluation when the v2.0.0 stable is released (and hopefully docs are updated)

As a result, it seems we can use the `distribution` project from docker or `zot`. We need to evaluate them again when
starting to work on this.

## Implementation plan

- prepare and deploy `distribution` cache instance, configure it for the new repo
  - ensure monitoring and alerting
- switch container runtimes to use the cache as a source of images and upstream `gsoci` as a fallback

## Open questions

1. Where to host the cache?

   The disk requirements for a cache might be significant and as a result cost of running an instance per MC can be quite
   high in total. Additionally, we can expect many of the images to be the same for all clusters (MCs and WCs) that run
   for the same provider. So, it seems running a single instance of the cache per cloud provider can be both much cheaper
   and also more efficient and performant.

   It seems that hosting 1 cache per MC will be too expensive and inefficient at the same time, therefore we want to
   try hosting a cache per-region and provider. In this case, it probably should be Giant Swarm, who hosts and covers
   the cost of the cache, as the cache will be configured to catch only images we need for our services (our public
   infrastructure images), but not customers. If customers need a caching solution as well, we will think about
   deploying it separately, probably in customer's MC.
