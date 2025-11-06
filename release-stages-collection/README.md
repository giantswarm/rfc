---
creation_date: 2025-11-06
issues:
  - xxx
last_review_date: 2025-11-06
owners:
  - https://github.com/orgs/giantswarm/teams/team-honeybadger
state:
summary:
---

# Release Stages for Apps in Collections

ToC:

- Intro
  - Problem Statement
  - Current status
  - Goals, non-goals, assumptions
    - non-goals: apps other then collections, no automatic propagation/promotion
    - assumptions: Apps -> HR migrated; auto upgrades handled in a separate RFC
- Design proposal
  - New collections layout in MCB
  - integration with GCS
  - Examples
    - overriding versions at different Stages
    - adding/removing app in different places
    - providing and overriding config in different stages
- Alternative solutions
