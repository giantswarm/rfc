---
creation_date: 2024-05-22
issues:
- https://github.com/giantswarm/giantswarm/issues/30631
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
state: review
summary: This contains the process for proposing, discussing, and formalizing technical decisions. It also introduces the RFC structure.
---

# Structured way to propose, discuss, and formalize technical decisions within an organization

### Problem statement

The technical decision-making process within our organization was found to be suboptimal, particularly when decisions impact multiple teams. The lack of well-defined steps towards a decision leads to confusion, delays, and suboptimal outcomes.
We need a more structured approach to proposing, discussing, and formalizing decisions to improve collaboration and decision quality.

The first [RFC and decision making process](https://handbook.giantswarm.io/docs/rfcs/decision-process/) proposed a file structure and introduced an overview of RFCs in the [Handbook](https://handbook.giantswarm.io/docs/rfcs/).
It also suggested a process for submitting an RFC for a technical decision.

This RFC extends the latter with a structure and introduces fields necessary for submitting a decision proposal.
Making our RFC framework more rigid will help reach decisions and specify who the decision maker is, for whom it is mandatory to provide feedback, and in which timeframe. Additionally, it includes a communication plan to ensure clarity and alignment.

To provide an example, this RFC is itself in the proposed structure.

### Decision maker
Team Horizon

### Deadline
13.06.2024

### Who is affected / stakeholders
- Product Owners
- Platform Architects
- Team Horizon

### Preferred solution

#### Technical decision-making process:
- Proposal Creation: Any team member can create an RFC document to propose a decision. See [RFC and decision making process](https://handbook.giantswarm.io/docs/rfcs/decision-process/) for a description of submitting an RFC.
- Review and Discussion: The RFC is shared with relevant stakeholders for review and feedback.
- Decision Meeting: If there is no agreement or insufficient feedback before the deadline, the decision owner schedules a formal meeting with relevant stakeholders to discuss the RFC and make a decision.
- Approval and Implementation: Once agreed upon, the decision is documented, and an implementation plan is created.
- Feedback: Retrospective sessions with the stakeholders are recommended, during and after the implementation, to evaluate and document the impact of the decision.

####  Template for technical decision RFC:
- Title
- Problem statement
- Decision maker
- Deadline
- Who is affected / stakeholders
- Preferred solution
- Alternative solutions (optional)
- Implementation plan (optional)
- Communication plan

### Alternative solutions
- Continue with current methods:
  - Pros: No change required.
  - Cons: Inefficiencies and inconsistencies remain.

- Adopt a free-form document process:
  - Pros: Flexibility in document format.
  - Cons: Lack of structure can lead to confusion and missed details.

### Implementation Plan
Preparation Phase:
 - By 13.06.2024: Develop the RFC template and guidelines.
 - By 01.07.2024: Onboard main stakeholders on the new process.

Full Rollout:
 - From 01.07.2024: Implement the process organization-wide.

Ongoing:
 - Monitor the process and refine it based on feedback.

### Communication plan
Documentation:
- Share the RFC template and guidelines in the Handbook.

Kickoff Meetings:
- Present the final process in SIG Product and SIG Architecture syncs.

Regular Updates:
- Provide regular updates on the process in SIG Product and SIG Architecture syncs and gather continuous feedback for improvements in 1:1s and Product & Engineering team reviews.
