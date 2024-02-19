---
creation_date: 2024-02-07
issues:
- https://github.com/giantswarm/giantswarm/issues/29503
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
state: review
summary: Revamp our docs to describe the Dev Platform product, considering the new Cluster API (CAPI) architecture. Temporarily move vintage to a subpath and create the new content in the top level. The docs entry point can still point to the old till renovation is over.
---

# Revamp our docs

## Intro

As part of the [Documentation Overhaul](https://github.com/giantswarm/giantswarm/issues/29503) that Horizon is working on during the first quarter of 2024 there was an idea of how to transition our current docs to a desired state where the new Dev Platform product is described correctly and precisely.

## State of the documentation

Our [current documentation hub](https://docs.giantswarm.io) is an ongoing effort to maintain old Vintage entries that are no longer valid in our new product, and at the same time adequate to the new Dev Platform and CAPI concept.

Today we have several work streams trying to achieve that goal:

1) Horizon and SIG docs maintaining a coherent docs structure that follows new product developments.
2) Teams updating doc entries for out-of-date documents. Most of the time they don`t have the time to rewrite the content to make it Platform/CAPI ready, so they stay out of date.
3) Teams, KaaS and platform, adding new content that is only working for the new implementations (CAPI).

## Goals

The described scenario is not working and ideally we find an alternative that has these goals:

- Have a good documentation portal that does not have entries out of date. Only new implementation (since we have completely deprecated Vintage).
- Stop trying to bring current articles to life, most of them are no longer valid in the new implementation. Just add what is relevant and possibly identify spots to fill by teams.
- Have a period for transition where everyone can look for content in Vintage and Dev Platform docs. Customers or support still have access to Vintage docs but new docs are also available.

## Process

Instead of creating a huge Pull Request in [our docs repository](https://github.com/giantswarm/docs) where we work in parallel (accumulating a lot of changes and configuration drifts), I propose to create a new clean space in our docs site. This new path is visible in as top level docs though the entry page still point to the old docs content. That way we can visualize the changes till we reach a point of satisfaction and furthermore, customers are migrated from Vintage product.

**But why?**

- In the new path we can create a structure according to the new necessities without having to transition from existing content.
- We don`t need to maintain aliases or links to old entries or sections.
- It is way easier to organize the work between teams to add needed minimal content for every section.
- We can work in iterations.
- Both docs sites will be publicly available.
- The end result of our docs will be simpler and cleaner since we are not influenced by old structure and content.

**How?**

General steps to achieve the aforementioned goals:

1) Moved the `vintage` content to a subpath so we leave a clean space in the top level docs site.
2) Add aliases from old content entries to include the old path so we don`t break links.
3) Leave the main docs entry page where it is now but pointing to the vintage path, so the appearance still the same.
4) Avoid bots to scrape the docs from now on to avoid temporal indexes. Add a banner to the vintage path to warn users of the state.
5) Work iteratively by top-level section adding new content (Ex: Platform Overview, Getting Started,...)
  2.1) Team Horizon will create a the top-level structure proposal. It will be mapped from [here](https://miro.com/app/board/uXjVO2Dh15w=/). When SIG docs and teams approve it,  we will create the structure empty.
  2.2) Identify owners for the sections to be completed, created or adapted. Create tickets for teams. Help and guide them to complete it. Think of the docs entry structure to have a similar outline for similar pages.
6) Iterate over step 2 till all top-level sections are done and we are happy with the current state. At this point change the main docs entry to point back to the top level docs and add a banner to inform this is our current documentation and the old one is under vintage subpath.
7) Once we migrate all customers (or almost) from vintage, we can decide to remove the vintage folder.

## Few clarifications

- This is a proposal, feedback welcome.
- I have consider migration within the repo and it will be way complex and difficult.
- We don`t plan to change the style at the moment. But we might align with handbook and intranet.

## References

- [Epic ticket](https://github.com/giantswarm/giantswarm/issues/29503)
