---
creation_date: 2026-01-30
issues: []
owners:
- https://github.com/orgs/giantswarm/teams/team-cabbage
state: review
summary: Use wildcard TLS certificates on management clusters with Envoy Gateway to eliminate per-service domain configuration in gateway-api-config.
---

# Wildcard TLS Certificates for Envoy Gateway on Management Clusters

## Problem Statement

Currently, TLS certificates for services exposed through Envoy Gateway on management clusters are managed by the `gateway-api-config` app using a single Certificate resource with multiple Subject Alternative Names (SANs). Each time a new application requires a domain, it must be explicitly added to this list.

This approach creates friction:

- **Manual configuration updates**: Every new service requiring a domain triggers a change in `gateway-api-config`.
- **Developer experience mismatch**: Teams familiar with Ingress expect domain configuration to be handled at the HTTPRoute level. The current requirement to update a central certificate configuration is unexpected and causes confusion.

## Proposal

Use a **wildcard TLS certificate** (`*.baseDomain`) per management cluster to cover all services, eliminating the need for per-service domain configuration.

### Key Changes

1. **Certificate configuration**: Replace the multi-SAN certificate with a single wildcard certificate (`*.baseDomain`) in `gateway-api-config`.
2. **ACME challenge method**: Switch to DNS-01 challenge validation, which is required for wildcard certificates. Some clusters may need to migrate from HTTP-01 to DNS-01.

### What This Enables

- Teams can define HTTPRoutes for any subdomain under `*.baseDomain` without requiring certificate configuration changes.
- The developer experience aligns with expectations from Ingress-based workflows.
- Reduced operational overhead for certificate management.

### Scope and Limitations

- **Services within `*.baseDomain`**: Automatically covered by the wildcard certificate.
- **Services outside `*.baseDomain`**: Custom domains or the bare `baseDomain` itself will still require explicit certificate configuration, as they do today.
- **Domain discovery**: Remains at the Gateway level. This is an Gateway API architectural constraint, not something changed by this proposal.

## Alternatives Considered

### 1. Keep the Multi-SAN Approach (Status Quo)

Continue using a single certificate with explicit SANs for each service domain.

**Pros:**
- No migration effort required.
- Explicit list of domains provides visibility.

**Cons:**
- Requires configuration updates for every new service.
- Creates confusion for teams expecting HTTPRoute-level domain handling.
- Operational overhead scales with number of services.

### 2. Per-Service Certificates

Issue individual certificates for each service using cert-manager's Gateway API integration.

**Pros:**
- Fine-grained certificate management.
- Certificate compromise affects only one service.

**Cons:**
- **Does not solve the core problem**: Domain discovery happens at the Gateway level in Gateway API, not at the HTTPRoute level. This means `gateway-api-config` would still require updates for each new service domain.
- Increased certificate management complexity.

## Implementation

### Prerequisites

- DNS-01 challenge support must be available for the cluster's DNS provider.
- cert-manager must be configured with appropriate DNS provider credentials.

### Changes Required

1. **gateway-api-config**: Update the Certificate resource to request `*.baseDomain` instead of listing individual SANs.
2. **cert-manager configuration**: Ensure DNS-01 solver is configured for the relevant DNS provider (e.g., Route53, CloudDNS, Azure DNS).
3. **Cluster migration**: For clusters currently using HTTP-01 challenges, migrate to DNS-01.

### Rollout

- Deploy to a test management cluster first.
- Verify certificate issuance and renewal with DNS-01.
- Gradually roll out to other management clusters.

## Security Considerations

- **Blast radius**: A compromised wildcard certificate private key affects all services under `*.baseDomain`.
- **Private key protection**: The certificate private key is stored as a Kubernetes Secret. Access should be restricted via RBAC.
- **Certificate renewal**: cert-manager handles automatic renewal. DNS-01 challenges do not require ingress exposure, which can be a security advantage over HTTP-01.
