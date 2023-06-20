# Ensure no single point of failure in management cluster access

## Access to management clusters for Giant Swarm staff

Our default access method to management clusters is now single sign-on (SSO).
For Giant Swarm staff this is currently done via Dex using GitHub as the _only_ identity provider (IdP).

Our vintage product also offers the possibility to create a client certificate to access the management cluster.
This means that in the event of GitHub or Dex being unavailable, we have a fall-back method for management cluster access.

For pure CAPI installations on the other hand, the only fallback authentication method is a single static kubeconfig that is stored in LastPass.
Since this method is currently not integrated with our tooling, accessing the management cluster using `opsctl` is not possible when there are problems with OIDC or GitHub.

Furthermore, loss of access to the management clusters implies loss of access to all workload clusters that do not have OIDC access for Giant Swarm staff set up.
This is due to the fact that in order to create a client certificate for these workload clusters, we need to access the management cluster first.
At this moment this likely applies to all workload clusters on pure CAPI installations.

However, even if OIDC access to workload clusters was set up, with GitHub as the identity provider, we would still have the IdP as the single point of failure.

Hence the goal of this RFC is to ensure that management cluster access is highly available for operations through Giant Swarm staff in the future.

## References

- [PKI epic](https://github.com/giantswarm/giantswarm/issues/15981)
- [Issue regarding client certificate creation for CAPO ](https://github.com/giantswarm/giantswarm/issues/21740)
- [Story for backup IDP in dex](https://github.com/giantswarm/roadmap/issues/603)
- [Proposal to use Azure AD for GS staff](https://github.com/giantswarm/giantswarm/issues/21627)
- [Story for IDP and dex connector automation](https://github.com/giantswarm/roadmap/issues/1432)

## Proposed solution

### Redundant identity providers

- Azure AD as the primary identity provider
- Secondary identity provider

### Enable opsctl to retrieve kubeconfig from LastPass

For Giant Swarm staff, the `opsctl login` command is the preferred way to access the management cluster. In the future we aim to improve the command by letting it read the kubeconfig stored in a LastPass secret.

## Future outlook

- Potentially have a PKI for client certificate creation

### Client certificates

In the vintage product, client certificates can be created from outside the cluster using `vault` for signing.
At the moment this is not the case for the CAPI product.

- This method of authentication is completely separate from SSO and does not have shared dependencies.
- As of now, client certificate creation is harder to monitor and control than SSO.
- Client certificates should be short lived and therefore would need to be recreated by users frequently.
- A long living client-certificate granting admin access is a security risk since permissions can not be revoked.
- We do not want this to be the primary authentication method for human users. (That should remain SSO)
- If we want to support this, we need to decide whether we want to use vault or something else.
- Whichever method we choose, we need to ensure that TTL duration is limited to minimize the security risk.

Possible story for workload cluster access here:
- If we run `vault` or an alternative outside the MC, we could create workload cluster CA here before cluster creation, generate all required client-certificates from that CA.
- This would make MC and WC more independent
- Requirement to have clean separation of customer accounts

### Storing kubeconfig in LastPass

In the CAPI product, a kubeconfig is stored in LastPass as an emergency fallback, during the bootstrap process.

- This method of authentication is completely separate from SSO and does not have shared dependencies.
- It is not integrated in our tooling and we need to pull the kubeconfig using lastpass cli.
- As it is right now, access is neither easily revokable nor is there a rotation. 
- In case of a security threat this implies rotating the api server CA and all certificates.
- Since it is already integrated, it makes sense to keep it for emergencies while there is no alternative.
- If we want to support this for a longer time we need to improve security.
- We could support this as fallback method in `opsctl login` by managing access to lastpass.com or calling the `lastpass` CLI to ease operations.

Possible story for workload cluster access here:
- Use a controller on the MC to push WC client certificiates to lastpass
- This would make MC and WC more independent
- Would enable rotation of short lived certificates
- Alternatively we could write the secret to a gitrepo via `sops` instead of using `lastpass`

### Introduce a second identity provider for SSO

Dex supports a wide array of identity providers. Customers are already using many of them. At the present moment, giant swarm staff can only login using github.
However, we could add more providers.

- We favor SSO when it comes to identity management for human engineers.
- Could be introduced for workload cluster access as well.
- Using e.g. azure AD would make sense since customers are using it.
- We might be able to simplify account automation when using another identity provider than github.
- We would still have a dependency on dex and this method will not completely remove the single point of failure.
- Adding another provider might mean individual setup for each existing configuration. (e.g. in github individual apps are needed) We should avoid this if possible since it already does not scale.
- While dex allows an array of connectors, we currently use a fixed naming for our single `giantswarm` connector. We need to revisit what relies on this convention to ensure the second connector is equal.
- Regardless of other means auf authentication being implemented, adding another dex idp would be beneficial.

### Other methods

For the time being we focus on above mentioned means of authentication.
Service account tokens are another one which we could revisit in the future. However, to authenticate human users, SSO is preferred.

### Related stories

This discussion is focused on management cluster access by GS staff and removing the single point of failure here should remain the goal.
However, our chosen solution for other access related problems has impact on the issue of management cluster access by giant swarm staff. We should aim to resuse the same mechanisms for workload clusters and management clusters as much as possible. Likewise we should strive to dogfood mechanisms we offer to our customers.
On the other hand, we should be conscious of differences between access for automation and controllers versus access for humans. 
Related problems include:

- Access to management clusters for controllers
- Access to management clusters for customers
- Access to workload clusters for controllers
- Access to workload clusters by gs staff
- Access to workload clusters by customers

## Next steps

### Automation for SSO setup towards MC and WC

The goal is to have SSO access by default on all our clusters (MC and WC) and ease introduction of new identity providers.

- Automation to register callback URLs in identity providers for new installations/clusters.
- Automation for identity provider side settings.
- Creation of the admin group and rbac automation (admin groups needs to be a list)
- Adapting dex to combine default (automatic) configuration as well as user side configuration.
- Adapting kubectl gs to work with more dex connectors.
- Deprecate k8s authenticator
- Make OIDC a default in all clusters
- This would need athena, Ingress NGINX Controller, cert manager and dex to be default apps.

### Adding azure AD as a second identity provider for SSO

As a first step to mitigate the problem of a single point of failure, we want to introduce azure active directory as a second SSO identity provider.
This can be done in rainbow independently of new developments in terms of pki for capi.

- Proposed connector name: `giantswarm-ad`. We want to use the same pattern for other connectors. Adding or removing another connector should be repeatable and fairly simple
- Configuration on the azure side (application, groups, users)
- This provider will be the first one supported by above automation.
- Later: Add another connector and deprecating github

### Revisiting lastpass as a fallback

We already use lastpass as a fallback and we should keep it if possible. However, we should integrate it better.

- Think about how to limit duration and renew it more often.
- Include this fallback option in `opsctl login`

### Deprecate Auth0

We want to unify the way we authenticate to services. This also means deprecating auth0.
- Identify which services still use auth0.
- Migrate from auth0 to other identity providers. (Likely azure AD)
  
### PKI story and future of client certificates

This is largely reliant on the development of the CAPI product. Therefore we want to focus on SSO first and revisit client certificates at a later point in time.
Since we still have vault in the vintage product and use other fallback methods (lastpass) in CAPI, we can afford to wait.
