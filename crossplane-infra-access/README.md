# Crossplane infrastructure access

## Intro

Team Honeybadger is deploying Crossplane to MCs. Crossplane can be used to manage infrastructure on the cloud provider side by both us and out customers.

In order to do that, Crossplane has to be able to authenticate and authorize against the infrastructure provider. The access model that Crossplane uses depends on the user. By default, Crossplane doesn't require nor provide any access info. The administrator of Crossplane can create as many access secrets as he/she wants and can grant access to them to other Kubernetes users using the standard RBAC configuration.

Example:
1. Crossplane admin logins to an AWS account. In IAM, it creates two roles:
  - `s3-access` that grants permissions to use S3 only,
  - `db-access` that allows usage of RDS,
2. For both roles, the admin creates access keys. Then, access keys are saved as secrets in the kubernetes API.
3. The admin creates 2 `ProviderConfig` custom resources, named `s3` and `rds`, referencing respective Secrets with AWS API keys. Access to `ProviderConfig` is restricted.
4. The admin grants permissions with RBAC:
  - he/she allows access to `rds` `ProviderConfig` to the `db-automation` ServiceAccount in the `devel` Namespace
  - he/she allows access to the `s3` `ProviderConfig` to the `customer-admins` Group
5. From now on, respective SA and users belonging to the group can request Crossplane to manage (CRUD) resources in AWS.

## Problem

We want to configure all our MCs so that it's easy to use Crossplane by our internal (Giant Swarm) users.

Example:
1. We want to deploy Harbor to all CAPA MCs. Harbor needs an S3 bucket to work. How can we pre-configure MCs, so that it is possible to create the necessary buckets as part of Harbor App deployment?

Specific questions in regard to infrastructure provider access tokens:

1. Is it possible to easily mass-create a set of access credentials across multiple/all MCs?
2. What is a reasonable access scope of a default infrastructure access token?
3. Should there be a default infrastructure access token on each MC at all?

## Possible solutions

### 1. No default access token

As it's hard to create a limited yet elastic set of access permissions to the infrastructure, we provide no default config. Every user that will need to do something will have to manage access tokens on its own. Sample workflow: a user that needs access to S3, needs to create AWS Access Keys on each MC. Then, the user needs to encrypt them and add to the [management clusters fleet repo](https://github.com/giantswarm/management-clusters-fleet/) in `sops` encrypted form. As a result, access tokens are delivered to every MC and RBAC permissions to them can be handled easily as a common RBAC configuration delivered by Flux to every relevant MC.

Questions:
- Is it possible/realistic to automate creation of these access keys (same set of permissions, but on different infra provider accounts)? What about different providers (AWS vs Azure vs ...)

### 2. "Reasonable" access token by default

To limit the problematic side of creating access tokens with cloud provider's IAM solutions, we make a fire-once effort of creating a set of roles on each MCs' provider. That access token will have a 'reasonable' set of services permitted (for example S3, databases, logs, ...). Token will be saved in management clusters fleet repo and delivered to MCs. RBAC will be configured so that only users in the `giantswarm-admin` Group can access it.

### 3. Minimal default access token

This is exactly like 2., but we start with a limited set of service allowed (right now we know that we need S3, so we include S3 only). When more services are required, we add more permissions to already existing token.

### 4. IRSA + Role claims

According to [docs](https://github.com/upbound/provider-aws/blob/main/AUTHENTICATION.md) we should be able to mix IRSA and assumed Web Identity providers. In this solution, `Crossplane` controllers run with a ServiceAccount that is authenticated by IRSA and authorized in IAM to claim other Roles in IAM. Then, we and customers can create multiple `ProviderConfig`s CRs that reference different IAM roles that `aws-provider` controller is able to claim using IRSA. This seems like a preferred solution, but has to be tested.

Problems/questions:
- This doesn't solve a use case, where clients (software) access to AWS infrastructure created by Crossplane needs to be based on access keys (we have this issue with Harbor). This can be worked-around by creating an IAM role, user and access keys from Crossplane, in the same go as the needed infrastructure, but this seems to be a complex and error prone solution.
- `aws-provider` controller still runs with a single SA (obviously). This means, that the IAM Role it runs with has to have permissions to claim all other needed IAM roles, including these created by a customer. And we don't want to edit our Role every time a customeror we adds another to-be-claimed Role.


