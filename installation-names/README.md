---
creation_date: 2022-09-07
state: approved
---

# Assigning installation names

The purpose of this RFC is to specify how we select installation names.

## High level process

- A Giant Swarm team is responsible for providing name candidates in a dedicated, public git repository.

- Customers, when preparing for a new installation, select a name from the repository. A pull request ensures that the claimed name is removed from the above repository.

## Providing name candidates

When providing name candidates, we apply the following criteria:

- ASCII characters a-z only
- Length minimum 5, maximum 8 characters
- Must not have been in use for an installation previously
- Should be easy to pronounce, to spell, and to type in an english language context
- Should not be used frequently in our communication

## Claiming a name

Customers should claim any name they like from our [repository](https://github.com/giantswarm/installation-names). The goal here is to foster adoption of the name.

We encourage customers to select a name that is not easily associated with the customer name. For example, a company named Jaguar should not pick the installation name `jaguar`.

Reasons are:

- Installation names may appear in many places, like log files, configuration files etc., where we do not intend to store customer information.

- If a customer grows from using one installation to using several, users might have a hard time understanding the inconsistency among the names.

The claiming of a name happens via a pull request that removes the name from the repository. The PR approval process should ensure that internal sanity checks are executed in order to verify the name as suitable.
