# Better control over changes in production environments

We currently use `flux` to deploy changes to our Management Clusters. `flux` is reconciling the `main` branch on different repositories.
We have some customers that don't want all changes to be deployed continuously to our production installations.
Instead, they want us to deploy to a testing installation first, and then deploy to the production installation during a maintenance window.

## Current solution

In order to do that, we keep `flux` suspended on this production installation while it's running on the testing installations. Then, we we want to upgrade the production installation, we manually resume `flux`, wait for the changes to be applied and suspend `flux` again.

## Proposed alternative

We create a new branch called `production` in the `capa-app-collection` and `config` repositories. And we make `flux` running in our production installation to target and reconcile this `production` branch. 
All testing installations will still use the `main` branch, we don't have to change anything there.
When we want to push changes to our production installation, we create a pull request to merge the last commits from the `main` branch into the `production` branch, and `flux` will take care of deploying the changes.

Because we create a pull request to push the changes to production, we automatically get an audit log of production changes. Also, changes can be reviewed before merging. 
With our current approach, it's not possible to know what have been merged since the last time that `flux` was resumed.  

Instead of having `flux` running on our testing environments while it's suspended on production, we keep `flux` running on all of them, making our environments more similar.
