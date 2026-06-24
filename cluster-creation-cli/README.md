---
creation_date: 2024-05-28
issues:
- https://github.com/giantswarm/roadmap/issues/2115
owners:
- https://github.com/orgs/giantswarm/teams/team-honeybadger
state: review
summary: Specification of a kubectl-gs command for creating a workload cluster in the Cluster API generation of the Giant Swarm platform
---

# CLI command for creating a new cluster

This RFC proposes the spec of a new command line interface (CLI) command to create a workload cluster in the Giant Swarm platform based on the Kubernetes Cluster API.

## Terminology

- **CLI** or **command line interface** refers to a text-based user interface to interact with a computer program.

- **Configuration** in the context of this RFC refers to the configuration of a workload cluster. This configuration is a set of properties that define the desired state of the cluster.

- **Cluster app** refers to a Helm chart that defines the resources to be created in the workload cluster. The chart is maintained by Giant Swarm and is versioned.

## Background

So far, Giant Swarm users created workload clusters mainly using these two methods:

- Via the `kubectl gs template cluster` CLI command
- Via the web user interface (happa)

As the command name `template cluster` suggests, the existing CLI method has been introduced with the goal to simplify the creation of a manifest, mainly by filling in some placeholders of a template. During the evolution that followed, flags have been added to allow configuring more and more details. But the command never kept up with the development of the underlying APIs. There were always some options that flags were missing for. Often, single flags were added and new releases were published, only to enable one more feature. As a result, users were required to stay up-to-date with their CLI, only to have all configuration options for clusters available. In addition, the multitude of flags made it hard for users to discover options. In addition, differences between providers sometimes required provider specific flags, while some flags could be used across (some) providers. Also the command never accounted for the differences between (vintage) releases, where a flag would only make sense in certain releases.

In short, the existing CLI method is extremely hard to use. For Cluster API (CAPI), we therefore decided to use a different approach.
In CAPI, clusters are deployed as apps (helm charts) via the app platform. Each app has a default configuration and users can override defaults according to their needs. The configuration schema is provided with the app and thoroughly maintained, including property titles, descriptions, example values, and value constraints like, for example, string validation patterns.

Our web user interface (happa) leverages these app's schema to dynamically generate a form which can be used to create a cluster configuration. Annotations from the schema, like title, descriptions, and examples, help the user decide which default values to override. Constraints help prevent mistakes like entering unexpected characters or numeric values outside certain limits. As we move towards Backstage plugins as our web UI, we plan to continue using this approach.

The new CLI command drafted here is supposed to make use of the above concepts, too. We want the command to work hand in hand with our web UI. More about this in the next section (TODO: which one?).

## Goals

- The command should provide an easy-to-use method for creating clusters, optionally assisted by a web UI to discover and configure options.
- The command should work the same way across all providers we support with Cluster API.
- The command code should require little maintenance. It should stay compatible with a large range of releases.

## Target use case

The most important use case we target with our CLI command is the creation of a short-lived cluster for testing purposes, as this is the likely the most frequent reason to create a cluster.

Production clusters, in contrast, are created much more rarely, often based on the experience gathered through testing with various clusters. Production clusters are also more likely to be provisioned through GitOps, while test clusters are often created and deleted ad-hoc.

## Requirements

- Users should be able to **re-use a configuration** they have used for cluster creation previously, optionally overriding only a few details.

- A **dry run option** should allow "previewing" the result without actually writing any resources to the management cluster.

- A **connection with the management cluster** should only be required to write resources. For a dry run, no connection should be necessary. (However, an internet connection will be required to access public information from GitHub repositories.)

- Configuration provided by the user should be **validated** against the apps's schema, and in case of validation errors, users should receive detailed feedback.

- Users should decide whether to actually create the cluster, or print a manifest only.

- A **cluster name must be provided by the user**. We won't generate a cluster name for the user.
  - At Giant Swarm we decided around November 2023 that we want users to set workload cluster names and avoid auto-generated names ([roadmap#2999](https://github.com/giantswarm/roadmap/issues/2999)). In theory, we could still offer an option (a flag) to auto-generate the name. However, this would require knowledge of the cluster-PROVIDER app schema in the command logic. For example, as of cluster-aws v0.73.0, the cluster name is set in the property .global.metadata.name. Although we are working towards alignment across providers, this may be different in other versions or other provider apps.

## Basic syntax

The command should be named `create cluster`, hence the entire command, without any flags, would be:

    kubectl gs create cluster

The most important flags would be:

- `--provider`: (required) provider name. For example: capa, capvcd, capz, eks.
  - TODO: How do we restrict and validate the provider list per installation?
- `--config`: Path to a config file (optional). Can be used multiple times. See "Configuration layering" below. As an alternative, or in addition, configuration can be passed via standard input.
- `--release`: the version number of the release to use. The release specifies the version of components to use in the cluster. If not specified, the latest release is used.
- `--namespace` / `-n`: the namespace in which to create the cluster. This is expected to be an organization namespace, like `org-myorg`.
- `--dry-run`: only validate the configuration and optionally print the resulting manifest.
- `--output`: This flag can be used to specify the format of the output when `--dry-run` is set. See the "Dry run output" section below for details.
  - `yaml` for a Kubernetes manifest that includes an App resource and one or several ConfigMap resources.
  - `config-yaml` for merged configuration YAML.
  - `command` for a self-contained representation of the command just executed, as a one-liner.
- `--set`: Override a configuration value. This flag can be used multiple times. The format is `path.to.property=value`.
  - Note: `--set` can only be used with scalar values (string, number, boolean, integer, etc.). It cannot be used to override an array or object.

### Examples

Ex. 1: Simple cluster creation based on a file

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --config myconfig.yaml

Ex. 2: Simple cluster creation based on standard input

    kubectl gs create cluster \
      --namespace org-test \
      --provider capa <<EOF
    global:
      metadata:
        servicePriority: lowest
        name: test01
        description: Just a test cluster
    EOF

While ex. 1 appears simpler and allows for easier re-use of a file-based configuration for a single user, ex. 2 has the benefit of being completely self-contained. It's a pure one-liner without the need for a separate file. This way it's easy to share the command, or copy the command from a website or web UI and paste it into a terminal.

Ex. 3: Overwrite a configuration value

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --config myconfig.yaml \
      --set global.metadata.name=test02

Ex. 4: Dry run

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --config myconfig.yaml \
      --dry-run

Ex. 5: Write the result to a file

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --config myconfig.yaml \
      --dry-run \
      --output yaml > manifest.yaml

## Dry run output

Combining `--dry-run` and `--output`, users can decide to print a representation of the desired cluster instead of creating it immediately.

Validation of the configuration provided should happen in any case, and an output should only be printed if the configuration is valid.

The following output formats are supported:

### `--output=yaml`

As is the case with many `kubectl create` commands, `--output=yaml` will print a full Kubernetes manifest of the resource to be created.

In our case, several resources are created, so the resulting manifest is a multi-document YAML.

This example command

    kubectl gs create cluster \
      --provider capa \
      --namespace org-myorg \
      --set global.metadata.name=mycluster \
      --dry-run \
      --output yaml

should yield the following output:

<details>

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mycluster-userconfig
  namespace: org-myorg
  labels:
    giantswarm.io/cluster: mycluster
data:
  values: |
    global:
      metadata:
        name: mycluster
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mycluster-default-apps-userconfig
  namespace: org-myorg
  labels:
    giantswarm.io/cluster: mycluster
data:
  values: |
    clusterName: mycluster
---
apiVersion: application.giantswarm.io/v1alpha1
kind: App
metadata:
  name: mycluster
  namespace: org-myorg
  labels:
    app-operator.giantswarm.io/version: 0.0.0
spec:
  name: cluster-aws
  namespace: org-myorg
  version: 0.76.1 # the latest version currently
  catalog: cluster
  config:
    configMap:
      name: ""
      namespace: ""
    secret:
      name: ""
      namespace: ""
  kubeConfig:
    context:
      name: ""
    inCluster: true
    secret:
      name: ""
      namespace: ""
  userConfig:
    configMap:
      name: mycluster-userconfig
      namespace: org-myorg
---
apiVersion: application.giantswarm.io/v1alpha1
kind: App
metadata:
  name: mycluster-default-apps
  namespace: org-myorg
  labels:
    app-operator.giantswarm.io/version: 0.0.0
    giantswarm.io/cluster: mycluster
    giantswarm.io/managed-by: cluster
spec:
  name: default-apps-aws
  namespace: org-myorg
  version: 0.52.0
  catalog: cluster
  config:
    configMap:
      name: mycluster-cluster-values
      namespace: org-myorg
    secret:
      name: ""
      namespace: ""
  kubeConfig:
    context:
      name: ""
    inCluster: true
    secret:
      name: ""
      namespace: ""
  userConfig:
    configMap:
      name: mycluster-default-apps-userconfig
      namespace: org-myorg
```

</details>

### `--output=config-yaml`

This output mode aims to provide a merged configuration YAML, which is the result of the configuration layering process. This is useful for debugging and understanding the final configuration that will be used to create the cluster, and will also help re-use the merged configuration in a future cluster creation.

The example command

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --set global.metadata.name=mycluster \
      --set global.metadata.servicePriority=lowest
      --dry-run \
      --output config-yaml

should yield the following output:

<details>

```yaml
global:
  metadata:
    name: mycluster
    servicePriority: lowest
```

</details>

Not shown in the above example, the output would also include all merged configuration passed via files (`--config`) and standard input.

### `--output=command`

This output mode aims to provide a self-contained representation of the command just executed, as a one-liner. This is useful for sharing the command with others, or for copying it to a script or a file.

The example command

    kubectl gs create cluster \
      --provider capa \
      --namespace org-test \
      --set global.metadata.name=mycluster \
      --set global.metadata.servicePriority=lowest
      --dry-run \
      --output command

should yield the following output:

```nohighlight
kubectl gs create cluster --provider capa --namespace org-test <<EOF
global:
  metadata:
    name: mycluster
    servicePriority: lowest
EOF
```

Not shown in the above example, the output would also include all merged configuration passed via files (`--config`) and standard input.

## Configuration layering

Configuration can be passed to the command in several ways:

1. Any number of YAML files specified via the `--config` flag.
2. YAML passed to standard input (STDIN).
3. Any number of single values defined via the `--set` flag.

The command will create one ConfigMap per source, and one [App](https://docs.giantswarm.io/vintage/use-the-api/management-api/crd/apps.application.giantswarm.io/) resource for the cluster-app. In the App resource, the ConfigMaps will be referenced under the `.spec.extraConfigs` property, which is an array. This way, the number of ConfigMaps is not limited.

The individual ConfigMaps' priority will be configured explicitly in the following order, where later sources overwrite earlier sources:

1. Each file specified via the `--config` flag, in the order they are specified.
2. Standard input (STDIN).
3. Each single value specified via the `--set` flag, in the order they are specified (All `--set` options should be merged into one ConfigMap, again where later values overwrite earlier ones).

This allows to override configuration from one file with a another file specified later in the chain, or with a value passed via STDIN, or finally with `--set`.

In other words, we leverage the App platform's configuration layering principle to provide a flexible templating mechanism, where the underlying layer is always provided by the app's default values.
As a usage example, this layering could be used to create a cluster using a template configuration file, and overriding some specific values via STDIN:

    kubectl gs create cluster --provider capa --config template.yaml <<EOF
    global:
      metadata:
        name: test02
    EOF

Alternative syntax for above example, using the `--set` flag:

    kubectl gs create cluster \
      --provider capa \
      --config template.yaml \
      --set global.metadata.name=test02

This enables the target scenario as described earlier, by re-using most configuration values from one file, and providing the required difference (here: the cluster name) via standard input. The same could of course be achieved by passing a second YAML file via another `--config` flag instead.

In input validation, each source is evaluated against the app's values schema independently. We avoid replicating any values merging logic (as known from helm or the app platform) into the kubectl-gs CLI code base.

## Progress display during creation

If the user chooses to create the cluster immediately (by not specifying an output destination or format), we want to provide detailed progress on the creation. The user should be encouraged to quit watching the progress at any time, without any effect on the provisioning progress.

We may even introduce another subcommand to continue watching the creation progress at any time.
