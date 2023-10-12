# OCI registry for China

## Intro

Please refer to <README.md>.

## Using ACR automated geo-replication for China

ACR is offered also in China, but after meeting some requirements. When they are met, it's possible to setup
automatic geo-replication between our registry in EU and China. That will allow us to save effort and complexity,
as we will no longer need direct images uploads to China (they make builds unnecessary long) nor sync them on our
own.

Plan:

- we apply for ACR in China
  - we have to go through [the formal procedure](https://learn.microsoft.com/en-us/azure/china/overview-sovereignty-and-regulations)
- we try to setup automated geo-replication between Europe and China
- switch China clusters to use the new ACR-China registry
- shut down `crsync` entirely
- delete Aliyun registry
