---
creation_date: 2021-11-24
issues:
- https://github.com/giantswarm/giantswarm/issues/19349
last_review_date: 2024-02-24
owners:
- https://github.com/orgs/giantswarm/teams/team-horizon
state: approved
summary: This RFC describes a general vision for improving the user experience of Managed Apps.
---

# Managed Apps Vision

This RFC describes a general vision for improving the user experience of Managed Apps.

With a previous iteration of the structure of Giant Swarm, one team was responsible for all of the managed apps. As the number of apps that Giant Swarm managed increased, it became more difficult to own these apps.

Giant Swarm has updated its structure so that ownership of apps is spread across multiple teams - instead of one team owning all apps, each team owns a number of apps. Each team is now responsible for an area of solutions, such as monitoring, and are then responsible for apps that help in that area, such as Prometheus. This ownership also includes concepts such as trainings or sales enablement. We've been referring to this concept as 'holistic ownership'.

With this change, more teams and more people are working on apps, overall. This means we can spend more time on each app, and provide a better user experience overall - we can start working more _deeply_.

As some examples of what working more deeply on apps means:
- Working upstream to fix specific customer issues, or provide feedback to maintainers on issues with upgrade paths.
- Building more application specific monitoring and alerting, so Giant Swarm is aware of application level issues before customers.
- Improving support for automatic scaling, so apps don't OOM on larger clusters, or scale on custom metrics.
- Building dashboards (or reusing upstream dashboards) and making them available to customers.
- Working with the incident and postmortem workflows to ensure that issues with applications are learnt from, improved upon, and applied to all customers.

These are just examples - it is up to each team to identify how to provide a better experience with the apps they manage. Overall, we should be aiming to improve our operations of managed apps, and reduce the amount of work our users need to do.

There are going to be situations in the future where we need to work directly with customers on managed apps, as the line of responsibilities becomes better defined. We should identify where we can help reduce the operational work customers need to do, and then do so - managed apps means we help with the management of apps.

Upgrades are one example. Giant Swarm can work with customers to help discover what is blocking customers from upgrading, and then help remove these blockers, such as with major version upgrades that require user interaction. Ideally, all customers run on the latest version of apps. We can improve our automation in future to start rolling out minor and patch versions automatically.

Giant Swarm should ensure that new versions of applications are available as quickly as possible - ideally, within hours of new versions being available upstream.

As another example, one customer cannot use automatic scaling for ingress controllers, as their network traffic spikes with certain events too quickly for automatic scaling to deal with. This means they need to manually scale beforehand. We can provide a better experience - for example, providing a system that allows for scheduling a scaling event in future. This would reduce the user's overall operational load, and provide a more managed experience.

These are examples of a more general idea - identifying customer problems with managed apps, working together to find a solution, and then building that feature. Ideally, this could even be pushed or integrated upstream, or provided as a generic, open-source solution. As usual, we should evaluate whether developing a solution into a feature is worth it - for example, because it helps multiple customers, or reduces toil.

To sum up - Giant Swarm should be continuously improving the operations of managed apps, both to improve the overall user experience, and reduce our user's operational load for managed apps. Managed apps are managed.
