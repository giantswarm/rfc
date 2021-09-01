# Sharing responsibility and customization with customers

## Problem Statement

We want to ...
1. give customers greater control over how their clusters are defaulted.
2. enable customers to have more agency in upgrading individual components.

## Enabling customer access

We have to be able to give customers access to the `git` source in a gitops setup in order to allow effective modification of any configuration.

We already have a shared repository in the Giant Swarm organization with each customer individually.
It is therefore logical to utilize this shared repository as a source for gitops related data.

## Enabling customer collaboration

We can lower the barrier to entry by using a repository which is already shared with a customer which they are already familiar with.

The following setup can allow us to maintain a high degree of control:
- Make the account engineer assigned to the customer a mandatory reviewer
- Utilize `CODEOWNERS` files to split responsibilities between Giant Swarm teams
- Allow the customer to make `Pull Requests` but not self approve
- Allow all Giant Swarm employees to review and approve `Pull Requests`
- Require at least one approval before merging

The desired outcome would be increased involvement of our customers in their own configuration.
