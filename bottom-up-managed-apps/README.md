**tl;dr Let’s offer only apps that we actually use as managed apps (of course, if customer also uses it or wants to use it), such as prometheus, oauth2-proxy, etc. and NOT: Linkerd, Harbor, etc. stuff on roadmap we don't actually use. This way, a small managed apps team can more effectively offer more managed apps for less effort, while retaining the same business and user value, which is reduce toil via managed apps. WDYT?**

----

This RFC arose from the idea to offer oauth2-proxy. It’s an app, which at least 2 of our customers really want (and I bet there are more), and I think we use. (See: [Slack](https://gigantic.slack.com/archives/CPC3M70UE/p1622729938024200))

**Proposal: Offer managed apps, bottom-up, instead of top-down. Get back to our ‘original intention'.**

Meaning:

1. List the apps we already use
2. Check which ones customers also already use or want to use
3. Prioritize those as managed apps
4. Grow our offering organically this way.

This is in contrast to the apps in our roadmap. That is, observabilty → developer tooling -> use cases (Kafka, etc.)... most of which are apps we don't already use internally, or merely feel we ‘should’ use but actually don't.

**Status Quo:**

Assumption: The basis on which the managed apps team was created is this idea:

> We use these apps already. Why not help customers with them as well? It won’t take much more effort.

What is happening:

- Somewhere along the way, we got lost… We offer and plan to offer apps we don’t use (but maybe think we ‘should’). As a result, the effort to do it is extensive.
- Ex — Kong, Aqua, Loki, and Linkerd and now maybe Harbor

The problem: Either we (1) don’t use these ourselves, or (2) Feel we ‘should’ use them, but don’t.

Either way, the result is our managed apps are ‘forced’. As a result, the effort to offer them as managed apps is not marginal, which I assume was the original intention. It’s a heavy lift, each app a struggle.

**Top 3 Benefits**

- **Increased speed - of adding managed apps, fixing issues, responding to support. Everything.** — The bottleneck of providing managed apps is having to learn a totally new app. Both technical (have to read up on documentation every step of the way) and psychological (uncertainty; fear of the unknown and not being an expert)
- **All the benefits of dogfooding**, most important of which are (1) improved product quality, (2) better product knowledge and awareness from first hand use, and (3) truly seeing other Giant Swarm engineers as customers, (4) we can more authentically evangalize this product because we chose to use it as well, (5) Better support since more GS engineers can offer expertise
- **Ability to manage more apps with current (small) number of people** — Because of the top two benefits above.

**Risks and Costs**

- Risk: Giant Swarm is not representative of our customers. So what we use and would dogfood would not apply to what our customers use.
- Cost: Not as "sexy” as ✨ shiny ✨ new ✨ apps ✨

**Next Steps / Questions:**

- What are some apps that (a) giant swarm uses and (b) at least 2 customers use?
   - prometheus
   - oauth2-proxy
   - …?
   - …?
   - …?
- Can we ‘package’ and sell these as managed apps even though they are not as sexy as shiny new apps?

