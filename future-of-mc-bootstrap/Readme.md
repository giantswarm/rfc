# Future of Management Cluster bootstrap and Creation


## Background

With the work of openstack team rocket started to work on a new way to create
management clusters. Goals were
- Full automation with as less interactive steps as possible
- Use CAPI clusters from the start
- Use Kubernetes native tooling instead of terraform and virtual machines
- Create a reliable way to recreate the management cluster from scratch if it
  is messed up by our tests
- Have a freshly created management cluster every beginning of the week to avoid
  configuration drift and manual changes sneaking in.

## Current state

- Implemented with bash and make.
- Automation still involves some manual steps for secret management and
  last pass access.
- With increased usage and accelerated growth of multiple teams using it some
  issues surfaced
  - No automated tests and CI, so that it is easy to mess it up for the other
    team
  - Bash / Make is not appreciated as a tool of choice by a some people
  - Secret management is hard to fully automate in its current starte
  - Credential creation is hard to automate as well (OIDC, Github, etc)
  - Manual CI by recreating test MCs on a weekly basis does not scale.

## Suggesstions to move on

### Short Term

- Separate build targets for different providers
- work on automated tests even if they are not perfect
- replace kubectl apply by our own tooling step by step

### Long term

- Split configuration management and secret creation out and create separate
  tooling for this
- Use zops instead of vault for secret Management
- Make bootstrap part as small as possible and hand over to flux as soon as
  possible
