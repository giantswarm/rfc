# Ensure no single point of failure in management cluster access

## Access to MCs for giant swarm staff in vintage vs the CAPI product

Our default access method to management clusters is now single-sign-on.
For Giant Swarm staff this is done via `dex` using github as the _only_ identity provider. 

Our vintage product also offers the possibility to create a client certificate to access the management cluster.
This means that in the event of github or `dex` being unavailable, we do not get locked out of the management cluster.

For pure CAPI installations on the other hand, no other authentication method is available at this point.
This poses a real risk to get locked out of the management cluster in case of problems with OIDC.
We also rely on the github api being available as an external dependency we can not control.

Furthermore, loss of access to the management clusters implies loss of access to all workload clusters that do not have OIDC access for giant swarm staff set up.
This is due to the fact that in order to create a client certificate for these workload clusters, we need to access the management cluster first.
At this moment this likely applies to all workload clusters on pure CAPI installations.

However, even if OIDC access was set up, it would still leave github as a single point of failure.

Let's ensure that management cluster access is highly available for operations through GS staff in the future.

## References

- [PKI epic](https://github.com/giantswarm/giantswarm/issues/15981)
- [Issue regarding client cert creation for CAPO ](https://github.com/giantswarm/giantswarm/issues/21740)
- [story for backup idp in dex](https://github.com/giantswarm/roadmap/issues/603)
- [proposal to use azure AD for GS staff](https://github.com/giantswarm/giantswarm/issues/21627)
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

### Storing kubeconfig in lastpass

In the CAPI product, a valid kubeconfig is stored in lastpass as emergency fallback. This is part of the bootstrap process.

- This method of authentication is completely separate from SSO and does not have shared dependencies.
- It is not integrated in our tooling and we need to pull the kubeconfig using lastpass cli.
- We should revisit how this works. What type of authorization is used here? Is access revokable? Is this rotated?
- Since it is already integrated, it makes sense to keep it for emergencies while there is no alternative.

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

Other than client certficiates, we could also look at service accounts as a means of managing access.

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

### Next steps

- to be discussed
