# OCI registry for Helm Charts

## Intro

Please refer to <README.md>.

## Helm charts OCI registry

The blocker for switching Helm Charts entirely to OCI is currently our artifact discovery process, which uses the
`index.yaml` file, that is available in HTTP based Helm registries only. So, to get started, we have to switch our
discovery process to OCI based one. Currently, we're already uploading our build artifacts to both HTTP and OCI repos,
so nothing is blocking implementation and a switch.

High level migration plan:

- prepare and deploy `distribution` cache instance, configure it for the upstream ACR registry
  - ensure monitoring and alerting
- switch our CI/CD pipelines to not tag dev build artifacts
  - we want to use retention policies for helm charts as well
- implement changes in the `app-operator`
  - use OCI discovery instead of `index.yaml` from HTTP registries
  - (optional) solve the problem of presenting only X (by default 5) most recent versions in the ACE CR
  - introduce a concept of primary and fall-back registry
- stop uploading charts into HTTP registries
- reconfigure `app-operator` to use the OCI cache as the primary registry and upstream ACR as fallback
- cleanup HTTP registries
- handle China as for images