# Handling Kyverno Policy Deployment

Our Kyverno policies have the following properties:
1. They are owned by different teams
2. They need to be deployed to different environments & on different providers
3. They require different testing setups according to 1. and 2.

Up until now we kept these policies in the same repository called `kyverno-policies`.
Now that we will have to rename the repository to upgrade Kyverno is an opportune time to discuss the future structure of our Kyverno policies.

## Proposals

These proposals are roughly ordered by the amount of repositories they would introduce by increasing order.

## Keep all policies in the same repository
It's simple, everything stays the same and `kyverno-policies` is just renamed.
### Pros
- Not a lot of effort
- Not much communication to make a change
- Single source of truth for all policies
### Cons
- Testing setup is complex as all different environments need to be covered in one repo
- Ownership is difficult as multiple teams own parts of the repo
- Upgrades are cumbersome

## Have one repository per team
Each team has one repository where it can put all its policies.
### Pros
- Each team has the power to make changes however they see fit
- Each team can handle their testing setup independently
- Only a limited number of repositories are changed
### Cons
- Components might change ownership and then policies need to be moved as well
- Teams often own multiple components and therefore adding complexity to the repo
- Teams need to maintain parallel test and delivery pipelines

## Have one repository per domain
Policies would be clustered by having one repository per domain.
A possible split of domains could be:
- Securiy
- Cluster Management
- App Management
- User Management
- Provider X specific
### Pros
- Domains can be matched to teams
- Manageable amount of repositories
- Clear separation of concerns
### Cons
- Defining domains is difficult
- Multiple teams likely feel responsible for the same domain (e.g. KaaS teams for Cluster Management)

## Keep policies together with application
Each app gets delivered directly with its policies.
### Pros
- Apps are tested together with their policies
- Apps and policies can change ownership together
- Upgrades can be coordinated easily
### Cons
- Policies are split across many repositories
- Some policies can not be matched to any app

## Repository per app and per team
Have one repository per team as well as delivering policies with apps (essentially combine the previous 2 approaches).
### Pros
- All benefits of packaging apps with policies
- Policies which can not be matched to any app, can live in the team repository
### Cons
- There are a lot or repositories
- Policies are split across many repositories
- Some policies can not be matched to any app


## Decision
We go forward with the `Have one repository per domain` proposal.

### Next steps
- Marcel (+ Zach) will work on removing policies from kyverno-policies and put them into domain buckets. Review from people and teams will follow then. Initial buckets will roughly fit team domains.
- We want to push testing policies together on a per environment basis. For WC this is test-infra, for MC this is a bigger story which intersects with other ongoing stories. Still we shouldn't forget this.
