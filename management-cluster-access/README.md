# Ensure no single point of failure in management cluster access

## Access to MCs for giant swarm staff in vintage vs the CAPI product

Our default access method to management clusters is now single-sign-on (SSO).
For Giant Swarm staff this is currently done via Dex using GitHub as the _only_ identity provider. 

Our vintage product also offers the possibility to create a client certificate to access the management cluster.
This means that in the event of GitHub or Dex being unavailable, we do not get locked out of the management cluster.

For pure CAPI installations on the other hand, the only fallback authentication method is a single static kubeconfig that is stored in LastPass for emergency access.
This poses a real risk to get locked out of the management cluster in case of problems with OIDC.
We also rely on the GitHub API being available as an external dependency we can not control.

Furthermore, loss of access to the management clusters implies loss of access to all workload clusters that do not have OIDC access for Giant Swarm staff set up.
This is due to the fact that in order to create a client certificate for these workload clusters, we need to access the management cluster first.
At this moment this likely applies to all workload clusters on pure CAPI installations.

However, even if OIDC access was set up, it would still leave GitHub as a single point of failure.

Let's ensure that management cluster access is highly available for operations through GS staff in the future.

## References

- [PKI epic](https://github.com/giantswarm/giantswarm/issues/15981)
- [Issue regarding client cert creation for CAPO ](https://github.com/giantswarm/giantswarm/issues/21740)
- [Story for backup IDP in dex](https://github.com/giantswarm/roadmap/issues/603)
- [Proposal to use Azure AD for GS staff](https://github.com/giantswarm/giantswarm/issues/21627)
- 

## Possible solutions

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

### Storing kubeconfig in LastPass

In the CAPI product, a kubeconfig is stored in LastPass as an emergency fallback, during the bootstrap process.

- This method of authentication is completely separate from SSO and does not have shared dependencies.
- It is not integrated in our tooling and we need to pull the kubeconfig using lastpass cli.
- As it is right now, access is neither easily revokable nor is there a rotation. 
- In case of a security threat this implies rotating the api server CA and all certificates.
- Since it is already integrated, it makes sense to keep it for emergencies while there is no alternative.
- If we want to support this for a longer time we need to improve security.
- We could support this as fallback method in `opsctl login` by managing access to lastpass.com or calling the `lastpass` CLI to ease operations.

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

### Service account tokens

Other than client certificates, we could also look at service accounts as a means of managing access.

- Service accounts can be rotated so they carry less risk in that regard than client certificates.
- This should not be a standard access method for human engineers.
- We would need to discover how to implement this. A dedicated controller for managing service account access is thinkable.

### Other access methods

- To be discussed

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

### Adding azure AD as a second identity provider for SSO

As a first step to mitigate the problem of a single point of failure, we want to introduce azure active directory as a second SSO identity provider.
This can be done in rainbow independently of new developments in terms of pki for capi.

- Proposed connector name: `giantswarm-ad`. We want to use the same pattern for other connectors. Adding or removing another connector should be repeatable and fairly simple
- Configuration on the azure side (application, groups, users)
- Automation to add new callback URLs for new installations/clusters.
- Creation of the admin group and rbac automation (admin groups needs to be a list)
- Adding the connector to our MC configurations.
- Adapting the dex helm chart.
- Later: Evaluate if this setup can be automated enough to make OIDC a default in workload clusters
- Later: Add another connector and deprecating github


### Revisiting lastpass as a fallback

We already use lastpass as a fallback and we should keep it if possible. However, we should integrate it better.

- Think about how to limit duration and renew it more often.
- Include this fallback option in `opsctl login`
