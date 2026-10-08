---
creation_date: 2026-10-01
issues:
- https://github.com/giantswarm/giantswarm/issues/37995
owners:
- https://github.com/orgs/giantswarm/teams/team-to-be-decided
state: review
summary: A guide for how we use AI when we write for colleagues. Respect the reader's time, write intentionally for your intended audience, and own what your agent says. Posts in #awesome-box, #random and #chat-x channels must be written by a human.
---

# AI etiquette

### Problem statement

More of our GitHub issues, pull requests and Slack messages are now written by AI. Much of it is long, which makes it hard to find the core point. Because of that, people give AI-generated content a lower priority, or ignore it entirely.

Some AI use also feels insincere. An AI-generated post that praises a colleague in `#awesome-box` doesn't mean the same as one written by a human.

This RFC doesn't stop anyone from using AI. It's a guide, so that our use of AI doesn't cost our colleagues time or trust.

### Decision maker

**To be decided.**

### Deadline

Q4 2026.

### Who is affected / stakeholders

All Giant Swarm staff.

### Preferred solution

We adopt the guidelines below. They are recommendations ("should"), except for the `#awesome-box` rule, which is mandatory ("must").

#### 1. Own what your agent says

You are responsible for everything your agent writes or posts for you. Read it before it goes out, because if you can't explain it, you shouldn't post it.

When an agent posts under your account, the reader should be able to tell. See [open questions](#open-questions).

#### 2. Respect the reader's time

Content for humans should be short and plain.

- Put the main point first.
- Cut background the reader doesn't need.
- Use plain words. [Simplified Technical English](https://www.asd-ste100.org/) is a good model.

#### 3. Write for your audience

Some issues and pull requests are for humans ***and*** agents. Put a short summary for humans at the top, with the detailed agent instructions below it. For example:

```markdown
## Summary

Two or three sentences for humans: what, why, and what you need from the reader.

<details>
<summary>Agent instructions</summary>

Detailed context, steps and acceptance criteria for agents.

</details>
```

#### 4. Write your own pull request descriptions

When an agent writes the code, you don't learn what you would have learned by writing it yourself. Writing the description is how you check that you understand the change, and reviewers get the "what" and the "why" in your words.

#### 5. Posts in `#awesome-box` must be written by a human

`#awesome-box` is where we thank colleagues for great work. Recognition only counts if you write it yourself, so don't use AI to write `#awesome-box` posts.

#### 6. Posts in #random and #chat-x channels must be written by a human

`#random` and `#chat-x` channels are primarily for discussion between people regarding the topic of the channel, and people usually post there to elicit replies from other humans. These channels should not be for messages posted by agents.

### Alternative solutions

- **Restrict AI-generated content.** Not chosen. AI can be useful. The problem is how we hand its output to other people, not the use of AI itself.
- **Make Simplified Technical English mandatory.** Not chosen. This is too strict for a guide, so we recommend it as a model instead.
- **Train Claude on the voice of each person.** Not chosen. It makes AI text look more human, but not shorter. It also makes AI text harder to identify.
- **Do nothing.** Not chosen. The problems above stay, and people keep ignoring AI-generated content.

### Implementation plan

Technical enforcement applies only to GitHub pull requests and issues. Slack guidelines are social rules only.

1. Publish this guide in the handbook.
2. Add a human summary section to the issue and pull request templates.
3. Instruct agents how to write issues and pull requests in order to comply with these guidelines by modifying GS skills.
4. Examine a central configuration to control the verbosity of Claude.
5. Examine an "unslop" skill.
6. Examine labels that show the audience of an issue (human or agent).
7. Ask Team Bumblebee what they learned about AI content in pull requests and issues.

### Communication plan

- Announce the RFC in `#news-general` and ask for feedback on the pull request.
- After approval, announce the guide in `#news-general` and link to the handbook page.

### Open questions

- How do we mark AI responses that agents post under human accounts? For example, a prefix or a signature.
- Which GitHub labels do we use to show the audience of an issue?
- What did Team Bumblebee learn about AI content in pull requests and issues?
