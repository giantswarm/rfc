# A better customer email management solution

This RFC investigates ways for managing (urgent) requests from customers received via email.

## Current setup

In case of urgency, customers can open urgent tickets by sending an email to urgent@giantswarm.io. This will automatically create a ticket in Opsgenie.

In case of non-urgent need, customers can open tickets by sending an email to support@giantswarm.io. This will automatically be forwarded to the #support channel in Slack.

While this works -also thanks to the fact that the tickets are broadcast- we reckon that, as Giant Swarm grows and gathers customers, having such general entry points can become hard to scale and manage.

## Desired improvements

We would like to be able to configure email aliases (where *alias*="some smart way to express and parse a composite email address") with different formats. These aliases should follow an easily parsable and standardized structure, which allows us to redirect the emails to the appropriate target.

For instance, some emails (`urgent`) could be ridirected to Opsgenie, while others (`support`) could be redirected to Slack.

A possible format could be the following: `customer-priority-area@giantswarm.io`. This would allow us to correctly address an email received from e.g. `adidas-urgent-aws@giantswarm.io` vs. `vodafone-support-security@giantswarm.io`. 

## Questions to answer

- would customers find this solution helpful and clear?
- which service could we use to deploy such a setup? For instance, would it be smart to exploit the plus `+` sign in email addresses or should we create real email addresses? In the former case, how could we trigger different actions depending on the portions of the address? Should we rely on Google or some other provider?
- is the current proposal for the structure of the email address fine? Should we include something else? Should we exclude something?
