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

## Some proposals

Here are some proposals for satisfying our goal.
These are by no means to be considered the *best* proposals for any definition of "best". These are just proposals.

### Proposal #1: an email address per customer

This proposal merges the concepts of:
-
- having a dedicated email address for each customer
- using the `+` sign trick to correctly redirect requests

Let's consider customer `shiba`. We can create a dedicated email address `shiba@giantswarm.io` and then use the `deliveredto` Gmail filter to filter emails out. Some examples could be:

- `deliveredto:"shiba+urgent+aws@giantswarm.io"`
- `deliveredto:"shiba+support+apps@giantswarm.io"` (or *packs* :) )

#### Pros

- when a customer joins/leaves we can simply create/remove the email address
- "low" price? One inbox per customer
- no alias logic involved: this is a real email address

#### Cons

- we have to manage the different combinations and one inbox per customer

### Proposal #2: just two email addresses

This proposal relies on using the `+` sign trick to correctly redirect requests.

We can define two email addresses: `urgent@giantswarm.io` and `support@giantswarm.io`.

Let's consider customer `shiba`. We can discern between their requests depending on the additional information present after the first `+` sign. Some examples could be:

- `deliveredto:"urgent+shiba+aws@giantswarm.io"`
- `deliveredto:"support+shiba+apps@giantswarm.io"` (or *packs* :) )

#### Pros

- no additional inboxes with respect to now
- no alias logic involved: these are a real email addresses

#### Cons

- we have to manage all the different combinations in the same inbox
- when a customer leaves, we may need to go and modify some rules rather than simply deleting an inbox
  - admittedly, we think and hope there won't be that many customers leaving us

## Questions

The following questions arise for both proposals:

- having the customer in the email is not really useful at the moment. Should we still go for it "just in case"?
  - it doesn't hurt
- can we choose the action to be taken (forward to slack/opsgenie) depending on the `deliveredto` address?
  - YES, we can!
- can the various processes be automated somehow? Maybe using a [Google Apps Script](https://script.google.com/)?
  - (scenario 1) email address creation/deletion
  - (both scenarios) "routes": support to slack vs. urgent to opsgenie; different areas
  I haven't been able to find a sensible solution so far, but we can dig into this a bit more.

# Final thoughts

Considering the pros and cons of each solution, I believe we can proceed as follows:

- Only use the support@giantswarm.io and urgent@giantswarm.io email addresses
- Specify area and customer using the + symbol, e.g. support+adidas+kaas@giantswarm.io
  - the customer is not really useful at the moment, but we can keep it in case some use cases arise in the future
- Using Gmail filters, either forward that email to Slack or Opsgenie
  - as far as Slack is concerned, we can simply use the Email app
  - as far as Opsgenie is concerned, the Email integration allows for creating numerous email addresses, each of which will assign the ticket to a specific team
