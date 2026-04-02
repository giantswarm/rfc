---
creation_date: 2026-04-01
owners:
- https://github.com/orgs/giantswarm/teams/team-shield
state: review
summary: Offer unique, cryptographically provable identities for workloads managed by the Giant Swarm platform to enable secure communication, seamless authentication, and global integration.
---

# Workload identities as a platform feature

## Problem statement

Giant Swarm and customer workloads currently rely on either static, long-lived credentials (API keys, service account tokens, shared secrets) or OIDC configured per-application to authenticate with external services, with each other, and across clusters. This creates operational burden (rotation, distribution, revocation) and security risk (credential leakage, broad blast radius, secret sprawl).

As the platform has grown, it has become more inter-connected, and the fundamental architecture of the product is changing. It would be much easier to secure cross-cluster and cluster-external access if all applications already had a credential that could be used to identify themselves with another service.

This RFC describes the possible use cases, tradeoffs, and an approach to issuing those identities as a platform feature. This system would help to reduce or eliminate many shared secrets, would enable mTLS in most environments, and would provide a stable interface for external systems to use for connecting to Giant Swarm clusters and services.

### Note to reviewers

The author(s) suggest reviewing this in separate sessions. Specifically:
- read until the large stopping point heading
- think, jot down feedback on the purpose and use cases. Did we miss any? Are any junk?
- read the Open questions
- start reading again from the stopping point heading
- think, give feedback

## What is a workload identity?

For purposes of this RFC, a workload identity is a cryptographic credential issued to an application that allows it to prove it is a specific application belonging to a specific entity. The application holds a private key; the verifying party checks the presented certificate against a public trust bundle published by the issuing authority.

The scope within which identities are issued and recognized is called a trust domain. A trust domain is typically aligned with an organizational boundary (a company, a department, a platform) and is served by a hierarchy of certificate authorities that sign and issue certificates for the applications within it.

The credentials issued for workload identity purposes are very short-lived and rotated automatically.

Credentials must be made available to the identity holder and the application must be configured to present the certificate, or use a proxy that does so on its behalf.

### Terminology

- **Certificate Authority (CA):** A system that signs and issues certificates. CAs form a hierarchy: a root CA signs intermediate CAs, which sign end-entity (workload) certificates. Trusting a root CA means trusting everything it has signed.
- **Federation:** The process by which two trust domains exchange trust bundles, enabling workloads in one domain to verify identities issued by the other.
- **Identity holder:** The application proving itself to another system. Also referred to simply as a client.
- **mTLS (mutual TLS):** A TLS connection where both sides present and verify certificates, proving identity in both directions.
- **OIDC federation:** A mechanism where an external service (e.g. AWS IAM) trusts JWTs issued by a SPIFFE trust domain via its published OIDC discovery endpoint, enabling workloads to authenticate with cloud providers without static credentials.
- **Relying party:** The service that verifies a presented identity and makes an access decision based on it.
- **SPIFFE ID:** A URI (`spiffe://<trust-domain>/<path>`) that uniquely identifies a workload. The path encodes attributes like region, application, and namespace.
- **SVID (SPIFFE Verifiable Identity Document):** The credential a workload presents to prove its SPIFFE ID. Can be an X.509 certificate or a signed JWT.
- **Trust bundle:** The set of root CA public certificates that a verifier uses to determine whether a presented certificate is trustworthy.
- **Trust domain:** The organizational boundary within which a single CA hierarchy issues identities. Two workloads in the same trust domain can authenticate each other directly. Workloads in different trust domains require trust federation.

## Use cases for validation

The following use cases drive the design. Each combines a relying party (who validates), an identity holder (who proves identity), and a scope.

1. **External service authenticates any Giant Swarm application globally.** An external API trusts "any Giant Swarm net-exporter" regardless of which customer cluster it runs in.
2. **External service authenticates Giant Swarm applications scoped to a customer or region.** A customer's S3 bucket trusts "Giant Swarm Falco in Customer X's clusters in Europe only."
3. **Customer workload authenticates any Giant Swarm application.** A customer application allows "any Giant Swarm Prometheus" to scrape it.
4. **Customer workload authenticates Giant Swarm applications locally.** A customer application allows "Giant Swarm Prometheus in this cluster" to scrape it.
5. **Giant Swarm service authenticates a customer application broadly.** A Giant Swarm API trusts "any Customer X Muster."
6. **Giant Swarm service authenticates specific customer application instances.** A Giant Swarm API trusts "Customer X's Jenkins in this cluster."

Bonus: connections where both sides have federated trust in the other can optionally be secured with mTLS.

### Discussion use cases:

7. **External service authenticates any instance of any customer application.** An external service trusts "any Jenkins belonging to any Giant Swarm customer".
Implementing (7) presents significant challenges with the current feature set of the proposed solution. Let's discuss if this is important.

8. **Offline management of air-gapped clusters.** It *is* possible to run a local trust domain behind an air gap. It _may_ be possible to maintain a *nested* branch of a *global* trust domain behind an air gap by updating intermediate key material out of band, or very infrequently, but that was not examined for this RFC.

### Use case dimensions

| Dimension | Values |
|---|---|
| Relying party | Customer workload, Giant Swarm workload, external service |
| Identity holder | Customer workload, Giant Swarm workload |
| Regional scope | Any region, specific region |
| Instance scope | Any customer/instance, specific customer/instance |

## Design constraints, assumptions, and challenges

### Constraints

1. The failure domain of any identity component must be limited to a **single region**.
2. The failure domain of any identity component must be limited to a **single customer**.
3. Giant Swarm is itself a customer of the platform.
4. If a customer leaves, their identity system must **remain operational** outside Giant Swarm.
5. Onboarding a new customer must require **no changes** to existing customers.
6. Customer on- or off-boarding must require **no changes** to pre-existing authorization policies.
7. No customer or entity may **impersonate or influence** another customer's identities, nor use the identities available to them to access another customer's system.

### Assumptions

- Every management cluster (MC) is per-customer, per-region. Customers have full access to their infrastructure. Giant Swarm operates within, but does not own it.
- Workload clusters (WCs) are managed by the MC and run both customer and Giant Swarm workloads.

### Challenges

- **Short-lived credentials require nearby issuance.** With certificate TTLs of ~1 hour, the issuing authority must be continuously reachable.
- **External validation must also be scoped and available.** Discovery endpoints / trust bundles for validation must be reliably reachable by external verifiers (AWS STS, Azure Entra ID).
- **Identity path design leaks information.** Paths encoding internal architecture (application names, customer names, regions) are visible to relying parties. The naming scheme must balance expressiveness with information exposure.
- **Global vs. local identity.** Some Giant Swarm workloads need a global identity (e.g. Mimir reporting to Grafana Cloud), while others need a customer-local identity (e.g. Alloy scraping endpoints that must survive customer offboarding). A workload may need both, and this need may change during its lifetime.
- **Customer lifecycle edge cases.** Departure-and-return, organizational splits, and acquisitions all affect trust domain naming and federation state.
- **Customers access MCs.** Customers would have access to key material stored in a management cluster.

---
## RECOMMENDED STOPPING POINT FOR FIRST REVIEW

Please stop reading here and think about this feature and its use cases at a high-level before proceeding to the technical weeds.

Then, skip to Open questions. Read them, and then continue on with the suggested solution.

---

## Suggested solution

We propose a **SPIFFE/SPIRE-based** workload identity platform with **two orthogonal identity planes**.

### Why SPIFFE/SPIRE

[SPIFFE](https://spiffe.io/) is a vendor-neutral identity standard which defines an identity format (SPIFFE ID), X.509 and JWT credential types (SVIDs), trust domain federation, and an OIDC discovery provider. [SPIRE](https://spiffe.io/docs/latest/spire-about/) is the runtime implementation (server) of the SPIFFE standard. It supports hierarchical CA topologies, pluggable attestation, and automatic short-lived credential rotation.

The CNCF-graduated projects have extensive support from community and commercial sponsors and widespread adoption, along with native integrations in other CNCF projects.

### Two identity planes

**Note:** A SPIFFE trust domain is an arbitrary string, and need not be a valid DNS domain at all. However, there are slight benefits if the trust domain does resolve to the location of the trust bundle for the trust domain.

Constraints 1–2 and 4–7 require isolated, customer-owned trust domains. But use cases 1–2 require a single trust anchor that external services can federate with without per-customer configuration. No single trust domain satisfies both, so:

1. **Giant Swarm Platform identity plane** — One trust domain (`spiffe://wid.giantswarm.com`) for all Giant Swarm platform workloads across all regions and customers. Controlled entirely by Giant Swarm.
2. **Customer identity plane** — One trust domain per customer (`spiffe://wid.customer-x.com`), running in the customer's infrastructure with customer-held CA keys.

Federation between planes enables cross-domain authentication (use cases 3–6).

### Company plane topology

- A **central SPIRE root** hosts the OIDC discovery provider and public federation bundle endpoint.
- **Regional SPIRE servers** receive intermediate CAs with 24-72h TTLs to mitigate temporary central outages.
- In each customer cluster, a **company SPIRE agent** (not a nested server) connects to the regional server. Agents hold only leaf SVIDs — no CA key material, so a compromised customer cluster cannot forge identities for Giant Swarm or other customers.

### Customer plane topology

- A **customer SPIRE root** runs in a dedicated WC and serves as the single root of trust for the customer's trust domain. Root CA keys are stored in the customer's KMS. It hosts the customer's OIDC discovery provider and federation bundle endpoint.
- Each **MC runs a nested SPIRE server** downstream of the customer root, receiving an intermediate CA with 24–72h TTL. This mirrors the company plane's regional server pattern.
- Each **WC runs a nested SPIRE server** under its MC. The entire hierarchy is within the customer's trust boundary.

This topology is structurally symmetric with the company plane: central root → regional/MC intermediates → cluster-level servers. The one intentional asymmetry: company SPIRE uses **agents** in customer infrastructure, while customer SPIRE uses **nested servers** — because the customer is the trust owner for their own domain.

**Customer root provisioning models:**
- **Model A (default):** Giant Swarm deploys and operates the customer SPIRE root in the customer's infrastructure as part of the managed platform. Root CA keys remain in the customer's KMS.
- **Model B:** The customer runs their own SPIRE root and provides configuration for MC SPIRE servers to connect as nested downstreams. This meets strict sovereignty requirements and would allow re-using an existing identity root.

### Federation

- Giant Swarm exposes its trust bundle via `https_web` (publicly reachable). Customer SPIRE roots fetch it without pre-shared secrets.
- Customer SPIRE roots expose trust bundles via `https_spiffe`. Giant Swarm regional servers federate per-customer — one `federates_with` entry per customer regardless of how many regions they operate in.
- **Onboarding**: add one federation entry. No existing configuration changes (constraints 5, 6).
- **Offboarding**: remove the federation entry. The customer's trust domain continues independently (constraint 4).
- **Adding a region**: no federation changes needed. The new MC connects to the existing customer root and is immediately part of the trust domain.

### Diagram

![Architecture Diagram](../@rfc/workload-identity/001-architecture-v2.png)

### SPIFFE ID scheme (draft)

Company workloads:

```
spiffe://wid.giantswarm.com/v1/<path-segments>/ns/<namespace>/sa/<service-account>
```

Customer workloads:

```
spiffe://wid.customer-x.com/v1/<path-segments>/ns/<namespace>/sa/<service-account>
```

The `v1` prefix enables future schema evolution.

The specific path segment ordering and whether paths reflect infrastructure topology or logical product structure are open decisions — see below.

### Credential lifetimes

| Credential | TTL | Rationale |
|---|---|---|
| Root CA (company or customer) | 5–10 years | Rotation requires re-establishing trust across all relying parties |
| Regional / MC intermediate CA | 24–72 hours | Survives temporary root unavailability; same pattern for both planes |
| WC intermediate CA | 12–24 hours | Shorter than MC intermediate; bounded by MC intermediate lifetime |
| X.509-SVID (workload cert) | 1 hour | Short-lived; automatic rotation via SPIRE agent |
| JWT-SVID | 5 minutes | JWTs are not revocable; minimize the replay window |

Regional and WC intermediate certs likely need longer lifetimes for semi-airgapped clusters.

### Constraint satisfaction

| Constraint | How satisfied |
|---|---|
| 1 — Regional failure domain | The customer SPIRE root is a cross-region dependency, under the same tradeoff as the GS regional SPIREs. Regional and customer MC intermediate CAs have sufficient TTLs to ensure continued SVID issuance during root outages. |
| 2 — Customer failure domain | Customer trust domains are fully independent. Company agents per customer are isolated from each other. |
| 3 — Giant Swarm as customer | Giant Swarm runs its own MCs/WCs with its own customer trust domain, same as any customer. |
| 4 — Operational after departure | Customer holds the SPIRE root, all MC/WC nested servers, and CA keys in their KMS. The entire hierarchy is in customer infrastructure. If Model A, the customer takes over operational responsibility for the root cluster. |
| 5 — New customer, no change | New trust domain + new agents + one federation entry. Nothing existing is modified. |
| 6 — On/offboarding, no authz change | Policies supporting wildcards are very flexible. All policies (even without wildcards) work for same trust domain. Cross-domain trust (e.g. a customer service trusting Giant Swarm applications) would need to be reconfigured. |
| 7 — No cross-customer impersonation | Separate root CAs per customer. Only GS leaf credentials in customer infrastructure — no company CA keys. |

## Open questions

1. **Semantic vs structural IDs.** Encapsulating customer and architecture information in an ID makes it easy to understand, but imposes rigidity, leaks information, makes and long-term assumptions that won't hold. Instead of `v1/giantswarm/platform/falco/v1-2-3/customer-x/eu-west-1/mc-name/wc-name`, consider `v1/giantswarm/platform/falco/v1-2-3`. The second more semantically identifies the application independently of the architecture, but additional work must be done to support cluster/customer/regions.

2. **What's in a name?** Especially if using structural names, what are the dimensions that must be included in the path?

3. **SPIFFE ID path segment ordering.** Should customer precede region (`/<customer>/<region>/...`) or follow it (`/<region>/<customer>/...`)? Zach is in favor of customer first, then region, if using structural IDs.

4. **Dual identities for Giant Swarm workloads.** Some workloads need both a global company identity (for external services) and a customer-local identity (for resources that must survive offboarding). It is possible to issue multiple identities to a workload, which must be aware of which to use. Is that useful? Should workloads receive SVIDs from both planes? What are the complexity and security implications?

5. **How many customer SPIREs?** In theory, we could operate customers with only WC or MC SPIREs, and not require both. The MC SPIRE could issue for all WC agents, or WC SPIREs could nest directly under the global root. The most resilient would be to use both.

6. **How/where does Giant Swarm run our regional SPIRE?** We can't (yet) run nested SPIRE servers within customer MCs because they would have access to key material that allows lateral movement to other customer trust domains. To keep "per-customer, per-region" failure domains, we would need to run a SPIRE server "next to" each MC, but in a place customers can't access. Where is that? (there is a future feature called "named path" support which may allow us to safely run it on the customer MC, but it's already years in the making).

7. **Air gap?** I think it makes sense to assume we need this eventually. Are there airgap-specific use cases?

8. **Support for external --> any customer authentication.** Use case 7 describes the possibility for an external service to authenticate "any instance of one|any application belonging to any Giant Swarm customer". This is currently very difficult to implement. The correct solution would involve identities signed by both Giant Swarm and the customer. This is not yet supported. So, how important is this use case?

9. **Customer SPIRE root placement.** The customer root needs to live somewhere highly available. Options include a dedicated WC in the customer's primary region, co-location in the first MC, a lightweight non-K8s host, or customer-provided infrastructure. The dedicated WC is the current recommendation, but introduces a single-region placement for a cross-region dependency.

10. **DNS and OIDC endpoint ownership model.** With a single trust domain per customer, there is one DNS name to manage (e.g. `wid.acme.example.com`). Should customers own this DNS and delegate to Giant Swarm during the relationship, or vice versa? Zach suggests customers own the DNS entry and point it back at their own infrastructure after offboarding.

11. **Agent attestation method.** More work is needed to investigate the technical means by which applications will attest in a cluster. Is someone interested in doing this?

12. **Network path: agent to regional server, and MC/regional to customer root.** How will agents reach their issuing servers? The MC→customer root connection is cross-region if the root is in a different region.

13. **Service mesh integration.** SPIRE can feed SVIDs to Envoy and Cilium. No investigation has been done on the technical details for that. Is someone interested in doing this?
