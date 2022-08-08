# Making parts of the intranet public

## Status quo

We currently have an internal `hugo` page which we use for internal documentation.
This page is called `intranet` and contains all kinds of documentation around our operational work as well as security and development.
The sourcecode for our `intranet` is in a private github repository which contains other security and business relevant data.

## Goal

The non-security relevant parts of the intranet should be public.
Making them public enables us to collaborate with other companies more easily.
It additionally allows us to enable outside contributors to work on projects more independently.

## Considerations

Content in the `intranet` is not fit for our general customer base.
It does not fit into our general product documentation but some of the content may be interesting to them.
I will not specify which parts of the current intranet may be better suited for our product documentation,
that is a decision which can be made independently of this proposal.

## Proposed solution

We create a new public repository called `handbook`.
This repository uses the same general structure and hugo setup as our intranet.

We then import the content from the `handbook` repository into the `intranet` source - this should be easily possible as described [here](https://discourse.gohugo.io/t/building-content-from-multiple-repositories/34636).
Importing the `handbook` repository will mean that the search functionality in the `intranet` will automatically scrape both private and public docs.
Therefore the `intranet` can remain as the single source of truth for Giant Swarm employees to aggregate information.

The `handbook` repository itself should also be setup with `hugo` to host its content under `handbook.giantswarm.io` making it easily accessible for outside collaborators.

The complete setup would then look as follows:
- `handbook` only contains information we are comfortable with having public.
- `intranet` only contains truly private information but imports all content from `handbook` into a unified search.
- `docs` contains product documentation which is directly linked on our website as before.

## Technical implementation

There are some open technical questions with this proposal.
1. Will it be possible to easily edit files from the hugo UI (e.g. edit button) even though the actual source of truth is split into 2 repositories now?
2. Will it be possible to structure the `handbook` repository in a way that it is a standalone hugo page but also easy to import into the `intranet`?

## Precedent in other companies

Gitlab follows a similar pattern as the one proposed here:
1. https://about.gitlab.com/handbook/ is the public documentation of gitlab itself (hiring, development, meeting guidelines, ...)
2. The private part is https://internal-handbook.gitlab.io/ but is insaccessible to the public.
3. https://docs.gitlab.com/ is the product documentation which is purely user focussed.
