---
creation_date: 2025-07-15
issues:
- https://github.com/giantswarm/roadmap/issues/2838
last_review_date: 2025-09-05
owners:
- https://github.com/orgs/giantswarm/teams/team-planeteers
state: approved
summary: This RFC addresses the strategic placement of operational runbooks to improve accessibility, maintainability, and security while ensuring consistent structure and content sanitization. Part of the work involves renaming the "Ops recipes" to "Runbooks" for clarity and alignment with industry standards.
---

# Strategic placement and standardization of operational runbooks

## Problem statement

Our operational runbooks (currently referred to as "Ops recipes") are currently scattered across multiple locations, specifically between our private intranet and public handbook. This fragmented approach creates several challenges:

1. **Inconsistent accessibility**: Some runbooks are private when they could be public, limiting knowledge sharing and community contribution
2. **Lack of standardization**: Runbooks follow different formats and structures across locations
3. **Security concerns**: Some runbooks may contain sensitive information that needs to be identified and sanitized
4. **Discovery issues**: Engineers struggle to find the right runbook when they're distributed across different platforms
5. **Maintenance overhead**: Managing runbooks in multiple locations increases the maintenance burden

We need a unified decision for runbook placement that ensures:

- Proper security and data sanitization
- Consistent structure and format
- Optimal accessibility for both internal teams and the community
- Clear governance and maintenance processes

### Who is affected / stakeholders

- Platform Engineers (primary users of runbooks)

### Preferred solution

Consolidate all runbooks in the intranet site with a (dedicated) section, following a standardized structure. Part of the work involves renaming "Ops recipes" to "Runbooks" to align with industry terminology and improve clarity.

#### Key components:

1. **Primary location**: Move all runbooks to a dedicated section in the intranet site (`docs/runbooks/`)
2. **Content sanitization process**:
   - In order to move the runbooks, we need to audit the documents for sensitive information (credentials, internal URLs, customer-specific data)
   - Create sanitized versions, removing or abstracting sensitive content, moving the sensitive information to the customers' repositories.
   - Establish guidelines for what constitutes sensitive information (this is already done)
3. **Standardized metadata structure**: the runbooks should follow a structured format frontmatter, including:
   - **Title and description**
   - **Owner**
   - **Last review date**
4. **Migration strategy**:
   - Phase 1: Decide the placement of the runbooks
   - Phase 2: Migrate all runbooks to the intranet, adding ownership and last review date—phase out the vintage runbooks.
   - Phase 3: Ensure all alerts and notifications are updated to point to the new runbook locations
5. **Governance model**:
   - Designate runbook owners for each recipe to ensure accountability
   - Add last review date to generate automatic reminders for updates

**Benefits:**

- **Improved discoverability**: Single source of truth for all operational procedures
- **Enhanced collaboration**: Easier for teams to contribute and update runbooks
- **Better maintenance**: Centralized location simplifies updates and version control
- **Consistency**: Standardized format improves usability and will make AI agents more effective in assisting with runbook-related queries

### Alternative solutions

#### Option 1: Keep current hybrid approach (intranet + handbook)

- **Pros**: No migration effort required; maintains current access patterns
- **Cons**: Continues fragmentation issues; doesn't solve discoverability or consistency problems; perpetuates maintenance overhead

#### Option 2: Create a dedicated runbooks site/platform

- **Pros**: Purpose-built for runbooks; could offer advanced features like search, tagging, analytics
- **Cons**: Additional infrastructure to maintain; splits documentation ecosystem; higher development and maintenance costs; potential for creating yet another silo

#### Option 3: Move everything to the public handbook

- **Pros**: Foster community contribution opportunities; it aligns with open-source principles;
- **Cons**: Security concerns about sensitive data; engineers reluctant to write in a public space; external users can benefit from runbooks

## References

- [Original ticket](https://github.com/giantswarm/roadmap/issues/2838)
