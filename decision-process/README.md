---
type: decision
stakeholders:
    - sig-architecture
    - team-horizon
    - team-team
issue:
---

# RFC Decision Making Process

This RFC follows on from the RFC repository README (see [here](https://github.com/giantswarm/rfc/blob/b3f4d2af6ff8965e542baae7d0e8fadb9163f356/README.md)).

This RFC aims to expand on the current RFC process by adding a lightweight decision making process.
The aim of this decision making process is to help enable, improve, and streamline technical decision making at Giant Swarm.

## RFC Types

To allow for a decision making process without removing the current free-form nature of RFCs, RFC types are proposed. The following changes will be introduced:

- All RFCs will have a YAML header (front matter)
- The YAML header will contain the following mandatory fields:
    - `type`

The 'default' type is `general`, and has no other requirements, to allow for free form writing. All currently merged RFCs would fall under this type, and will be moved to this type.

The following is an entire and valid example of a YAML header for an RFC:

```
---
type: general
---
```

## Decision Making Process

The two main aims of the decision making process are to ensure that the relevant groups have seen and approved the decision, and that the implementation of the decision is being tracked.

To that end, the `type` field can also be `decision`. It is understood that when a `decision` RFC has been merged, that the decision has been taken and agreed on.

If the `type` is `decision`, the following fields would also be mandatory:

- `stakeholders`
- `issue`

The `stakeholders` field is a YAML list of GitHub groups, e.g:
```
- stakeholders:
    - sig-architecture
    - team-horizon
```

This represents all the groups that need to particpate in the decision making process. For all the groups listed in the `stakeholders` field, there must be at least one approval from a member of that group for the RFC to be merged.

The `issue` field is a link to a GitHub issue where the work to implement the decision is being tracked. It is reasonable that the `issue` field is empty when a `decision` RFC is opened, and added when the general consensus for the RFC appears present.

The following is an entire and valid example of a YAML header for an RFC:
```
---
type: decision
stakeholders:
    - team-rocket
    - team-phoenix
issue: https://github.com/giantswarm/roadmap/issues/XXX
---
```

As another example, this RFC itself also implements the `decision` type RFC YAML headers.

## Automation

YAML headers will be checked and ensured by CI, specifically:

- That the `type` field is present and has the value `general` or `decision`.
- That the `stakeholders` and `issue` fields are present, if the `type` field has the value `decision`.
- That there is an approval from one member of each of the listed group, if the `stakeholders` field is present.
- That the value of the `issue` field is a valid GitHub Issue URL, if set.
