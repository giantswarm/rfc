# Relations of entities in the developer portal

This document outlines how we want to model relationships between the software components we develop, with the goal to simplify understanding the interplay and interdependencies in our software landscape.

Main questions/problems to solve:

- Which relationships should we present?
- How will relationships be modeled and maintained in both a technical and a workflow sense?

## Background

Since July 2023 we run an internal developer portal based on Backstage. The catalog is a directory of entities of various kinds. We currently use these kinds:

- **Component**: a software component, e. g. a service or a library.

- **Group**: represents a team we manage in GitHub.

- **User**: represents a person, a GitHub user and a member of a team in GitHub.

The Backstage catalog supports additional kinds, like API, Template, Resource, System, and Domain, which we don't use yet.

Entities can have various types of relations to other entities. In the user interface, this is display in various ways, including a graph visulization. There is usually also a way to use a relation for navigating back and forth between entities.

We currently present three types of releationships already:

- `ownedBy` / `ownerOf` between Component and Group, informing about the ownership if a software component.

- `memberOf` / `hasMember` between a Group and a User entity, showing who belongs to which team(s).

- `parentOf` / `childOf`: A parent/child relation to build up a tree, used in our case to describe the organizational structure between Groups. This could also be used for other entity kinds.

Backstage offers the following additional relationship types, which we don't use yet:

- `dependsOn` / `dependencyOf`: A relation denoting a dependency on another entity. This relation is a general expression of being in need of that other entity for an entity to function. It can for example be used to express that a website component needs a library component as part of its build, or that a service component uses a persistent storage resource.

- `partOf` / `hasParts`: A relation with a Domain, System or Component entity, typically from a Component, API, or System. These relations express that a component belongs to a larger component; a component, API or resource belongs to a system; or that a system is grouped under a domain.

Especially for entities of kind API:

- `consumesApi` / `apiConsumedBy`: A relation with an API entity, typically from a Component. These relations express that a component consumes an API - meaning that it depends on endpoints of the API.

- `providesApi` / `apiProvidedBy` is a relationship to express that a certain API (which is another type of catalog entity) is provided by a certain Component.

## Proposal

## Components depending on libraries

Let's have the dependency relationship between components and the libraries they are using visible in the portal. Here we refer only to the libraries we own (in Go that's any module named `github.com/giantswarm/*`), since adding entities for the thousands of third party libraries we use would bloat our catalog heavily and probably make it unusable.

In a Go project, the fact that a module depends on another module is encoded in the `go.sum` file. Alternatively, we can also investigate the [Github API for exorting a bill of materials](https://docs.github.com/en/rest/dependency-graph/sboms?apiVersion=2022-11-28).

Other languages we use (Python, JavaScript/Typescript, ...) have similar concepts and may be explored, however each of thise is only a niche in our landscape and we will have to evaluate whether the value gained is worth the effort.

## Components depending on other components (services)

We have cases where a certain service can only function when another service is also deployed with it. Examples:

- `kubectl-gs` (CLI) depends on `athena` (service) running in whatever cluster to sign in to.

- `api` (deprecated Rest API) depends on tokend, companyd, userd, cluster-service, credentiald.

- `cluster-services` depends on vault and kubernetesd.

- `passage` depends on `userd`.

TODO: Find some more modern examples

While some of these dependencies might be useful to depict, it's also possible to take this too far. For example, every app (as in the Giant Swarm app platform) relies on app-operator and chart-operator to deliver it. Howevwer, rendering this dependency for hundreds of apps is likely not helping anyone. So we need human judgement when deciding which dependencies to depict.

## App collections and the apps they include

TODO Can we detect an app collection?

TODO Can we find the apps belonging to a collection in a robust way? [Example](https://github.com/giantswarm/capa-app-collection/blob/2e34e0580e50418897d1b169771e3d92aadf4eb1/flux-manifests/athena.yaml)

## App bundles and the apps they provide

App bundles should point to the apps they provide, using the `hasParts` relation. In the opposite direction, this also means that from an app, there would be relation to an app bundle (or, potentially, several app bundles) including this app.

For example, the `security-bundle` should point to `kyverno`, `falco`, `starboard-exporter` and so on using the `hasParts` relation.

The data needed is already encoded in the [bundle values](https://github.com/giantswarm/security-bundle/blob/14eb70be3cf65f4b78c046a0bc3fa5ccca72c565/helm/security-bundle/values.yaml).

TODO: Verify how various bundles enode their child app info. Is this consistent?

TODO: Verify if we have a robust way to detect a bundle among other non-bundle apps.

