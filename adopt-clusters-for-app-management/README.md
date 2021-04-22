# Make it possible to manage apps and configuration on third-party clusters

As a user I can adopt an existing cluster and deploy and manage apps on this cluster. This existing cluster doesn't need to be a cluster that has been created by Giant Swarm. Apps and configuration get upgraded automatically via our App platform and across a fleet of non-GS clusters. Giant Swarm will also take care of 24/7 operations of these apps.

Benefits: New customers do not have to migrate their existing clusters to Giant Swarm to use a managed app from Giant Swarm
Challenges: Access to these clusters? Do we add our own RBAC for this as well? The clusters might be unreliable and in general this adds a lot of variety in terms of environments our apps need to work properly.
