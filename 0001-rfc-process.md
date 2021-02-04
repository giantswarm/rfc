# RFC 0001 - RFC Process

This RFC describes the RFC process for Giant Swarm.

Giant Swarm is a growing, distributed company, and we want to ensure that everyone continues to have the ability to bring their ideas and thoughts into the hivemind. While a large amount of our discussion currently happens successfully in chats and calls, a long-form writing process may provide some benefits: i.e: promoting deep thinking and dicussion, creating a record of considered ideas and discussion, reducing number of meetings (and allowing easier management of timezones), and providing avenues for increasing the asynchronousity of our work.

Before scheduling a call, or starting a Slack thread, ask yourself whether you could be writing an RFC instead.

All ideas, thoughts, comments, suggestions, and eldritch ramblings, are valid and welcomed as RFCs.

## Housekeeping

The following lists some basic formatting and houskeeping decisions concerning RFCs:

- RFC numbers must be unique and increasing (i.e: take the next available number).
- RFC filenames must be in the form `XXXX-$title.md`.
- RFCs must be written in Markdown.

The following lists some ideas towards RFC that are explicitly not presented:

- No formal structure (i.e: headers) is presented.
- No lifecycle (i.e: different stages of discussion or acceptance) is presented. This includes GitHub process - RFCs can be discussed as much as wanted in Pull Requests, and then merged as the author(s) see fit.
- No changes to ADRs or PDRs are presented.
- No minimum or maximum limits on size of RFCs are presented.

This is both to allow a more natural process to evolve over time, as well as to not prescribe a badly-fitting process too early. The above points could be the subject of future RFCs.

## Visiblity

The RFC repository (`giantswarm/rfc`) is private by default. This is understood to be contrary to Giant Swarm's default position of radical transparency. This is to allow for all ideas to be shared, without concerns of whether a concept is suitable for public discussion. 

In future, it should be possible to share select RFCs publically (i.e: via rendering RFCs to PDF for distribution), to allow for cases where we would like to share them externally.

## Sources

- [IETF, RFC 3](https://tools.ietf.org/html/rfc3)
- [Oxide Computer Company, RFD 1](https://oxide.computer/blog/rfd-1-requests-for-discussion/)
