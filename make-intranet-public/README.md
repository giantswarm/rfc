# Making parts of the intranet public

## Status quo

We currently have an internal `hugo` page which we use for internal documentation.
This page is called `intranet` and contains all kinds of documentation around our operational work as well as security and development.
The source code for our `intranet` is in a private GitHub repository which contains other security and business relevant data.

## Goal

The non-security relevant parts of the intranet should be public.
Making them public enables us to collaborate with other companies more easily.
It additionally allows us to enable outside contributors to work on projects more independently.

A very direct (and most urgent) goal is to enable outside collaborators quickly who need to work on docs for us.
This is mainly related to companies who will help us implement features in our managed apps but will not get full access to our private docs.

## Considerations

Content in the `intranet` is not fit for our general customer base.
It does not fit into our general product documentation but some of the content may be interesting to them.
I will not specify which parts of the current intranet may be better suited for our product documentation,
that is a decision which can be made independently of this proposal.

## Proposed solution

We create a new public repository called `handbook`.
This repository uses the same general structure and hugo setup as our intranet.

A similar search setup to our docs should be setup which covers the `handbook` as well as the `intranet`.
That search will then be accessible through the `intranet`, linking to both sources of truth.
Therefore the `intranet` can remain as the single source of truth for Giant Swarm employees to aggregate information.
Most importantly, it becomes trivial to link URLs from either source as search results will forward you to the specific article.

The `handbook` repository itself should also be setup with `hugo` to host its content under `handbook.giantswarm.io` making it easily accessible for outside collaborators.

The complete setup would then look as follows:
- `handbook` only contains information we are comfortable with having public.
- `intranet` only contains truly private information but imports all content from `handbook` into a unified search.
- `docs` contains product documentation which is directly linked on our website as before.

### Transitioning content into the public handbook

Content will be transitioned into the public handbook on a "if-needed" basis for now.
We have some usecases which require our internal docs to be public (e.g. relevant docs to external collaborators, people related docs which help with hiring, ... ).

Once the new concept is proven with the currently needed docs being public, then a `public by default` policy should be put in place.
This should then by followed by all non-critical docs being moved to the public repo in quick succession.

Docs should always be made public by the owners of the docs.

## Technical implementation

There are some open technical questions with this proposal.
1. Will it be possible to easily edit files from the hugo UI (e.g. edit button) even though the actual source of truth is split into 2 repositories now?
2. Will it be possible to structure the `handbook` repository in a way that it is a standalone hugo page but also easy to import into the `intranet`?

## Precedent in other companies

Gitlab follows a similar pattern as the one proposed here:
1. https://about.gitlab.com/handbook/ is the public documentation of gitlab itself (hiring, development, meeting guidelines, ...)
2. The private part is https://internal-handbook.gitlab.io/ but is insaccessible to the public.
3. https://docs.gitlab.com/ is the product documentation which is purely user focussed.
