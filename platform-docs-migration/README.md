---
creation_date: 2024-02-01
issues:
- https://github.com/giantswarm/giantswarm/issues/29503
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
state: review
summary: Revamp our docs to be Platform Dev ready considering the new Cluster API (CAPI) architecture. Instead of modifying existing docs content find a way to create a new site from a clean plate and avoid stale content.
---

# Revamp our docs

## Intro

As part of the Documentation Overhaul that Horizon is working on during first quarter of 2024 there was idea of how to transition for our current docs to a desired state where the new Dev Platform product is described correctly and precisely.

## State of the documentation

Our [current documentation hub](https://docs.giantswarm.io) is an ongoing effort to maintain old Vintage entries that not longer are valid for our new product and at the same time adequate to the new Dev Platform concept. Those are the current works streams our docs have today:

1) Horizon and SIG docs maintaining a coherent docs structure that follow new product developments.
2) Teams updating doc entries for out of date documents. Most of the times they don`t have the time to rewrite the content to make it Platform/CAPI ready, so they stays out of date.
3) Teams, KaaS and platform, adding new content that is only working for the new implementations (CAPI).

## Goals

- To have a good documentation portal that does not have entries out of date. Only new implementation (since we have completely deprecated Vintage).
- Stop trying to bring current articles to life, most of them are not longer valid in new implementation.
- To have a period for transition. Customer or support still have access to Vintage docs but new docs are also available.

## Process

Instead of creating a Pull Request in [our docs repository](https://github.com/giantswarm/docs) where we work in parallel (accumulating lot of changes and drifts in configuration), we create a new clean repository for the new docs. This new repo can be deployed in a temporal domain where we can visualize the changes till we reach a point of satisfaction and customers are migrated from Vintage product.

**But why?**

- In the new repository we can creating a structure according to the new necessities without having to transition from existing content.
- We don`t need to maintain aliases or links to old entries or sections.
- It is way easier to organize the work between teams to add needed minimal content for every section.
- We can work in iterations.
- Both docs hub will be publicly available.
- The end result of docs will be simpler and cleaner since we are not influence by old structure and content.

__Note__: Personally I was trying to deprecate a doc entry last week and spent more than an hour because link dependencies and inconsistencies in the content.

**How?**

General steps to achieve the goals

1) Create new repo for new docs hub. Just the skeleton, configuration, CI/CD and new domain/server.
2) Create the main structure. Already discussions [here](https://miro.com/app/board/uXjVO2Dh15w=/).
3) Migrate the part of the content already exist in the current docs.
4) Create tickets for the teams with missing documentation pages.
5) Once migrated all customer (or almost), move new docs to become our current docs. We can still maintain old docs in new domain (vintage-docs.giantswarm.io).

## Few clarifications

- This is a proposal, feedback welcome.
- I have consider migration within the repo and it will be way complex and difficult.
- We don`t plan to change the style at the moment.

## References

- [Epic ticket](https://github.com/giantswarm/giantswarm/issues/29503)
