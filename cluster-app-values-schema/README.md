# Basic requirements for cluster app values schema

Cluster apps are apps which are used to configure and provision clusters based on Cluster API in the Giant Swarm platform. Like all helm charts, these apps are configured using so-called values YAML files, which are passed to the app as a ConfigMap for cluster creation. The allowed structure of the values YAML is defined by the app's values schema.

This RFC defines basic requirements for all cluster apps provided by Giant Swarm.

## Overview

- [R1: JSON Schema dialect (draft 2020-12) must be specified](#r1)
- [R2: A single type must be declared](#r2)
- [R3: Explicitly cover all allowed properties](#r3)
- [R4: Array item schema must be defined](#r4)
- [R5: Properties must have a title](#r5)
- [R6: Properties should have descriptions](#r6)
- [R7: Some properties should provide examples](#r7)
- [R8: Constrain values as much as possible](#r8)
- [R9: Required properties must be marked as such](#r9)
- [R10: Use `anyOf` and `oneOf` only for specific purposes](#r10)
- [R11: Use `deprecated` to phase out properties](#r11)
- [R12: Provide valid string values where possible](#r12)
- [R13: Avoid recursion](#r13)
- [R14: Avoid logical constructs using `if`, `then`, `else`](#r14)
- [R15: Avoid `unevaluatedProperties`, `unevaluatedItems`](#r15)
- [R16: Array items and tuple validation](#r16)
- [R17: Common schema structure](#r17)
- [R18: Avoid using empty values in defaults](#r17)

## Background

TODO: Some more info regarding the rationale.

- In-place documentation of properties
- Better validation to catch configuration errors before they are applied
- Generated entry forms
- Generated information display
- Enabling processes and communication about explicit contracts instead of implicit behaviour

## Definitions

- **Cluster app**: App (as defined by the Giant Swarm app platform) that allows for provisioning a cluster in a Giant Swarm installation.
- **JSON Schema**: declarative language that allows to annotate and validate documents that are compatible with JSON.
- The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED",  "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html)

## Requirements

Requirements carry identifiers with prefix `R` and a unique number, for easy referencing.

### R1: JSON Schema dialect (draft 2020-12) must be specified {#r1}

Each cluster app's values schema file MUST specify the schema dialect (also called draft) used via the `$schema` keyword on the top level, with the draft URI as a value.

The draft URI MUST be `https://json-schema.org/draft/2020-12/schema`.

Example:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  ...
}
```

### R2: A single type must be declared {#r2}

For each property, including the root level schema, the `type` keyword MUST be present, and there MUST be a single value for the `type` keyword.

While JSON Schema draft 2020-12 allows multiple values for the `type` keyword, for cluster-apps this would complicate the generation of user interfaces. Hence we require a single type to be specified.

For validation, there is no difference between an array with a single member or a single string. The two following examples can be considered identical.

```json
{
  "type": "string",
  "title": "Name"
}
```

```json
{
  "type": ["string"],
  "title": "Name"
}
```

### R3: Explicitly cover all allowed properties {#r3}

All properties that can be used in values MUST be covered in the schema explicitly.

To enforce this and to disable the use of any undefined properties, the keyword `additionalProperties` MUST be set to `false` on the schema's root object.

For objects deeper in the schema hierarchy, keyword `additionalProperties` SHOULD be set to `false`, too.

### R4: Array item schema must be defined {#r4}

The items schema for all array properties MUST be defined using the `items` keyword.

### R5: Properties must have a title {#r5}

Each property MUST be annotated via the `title` keyword.

The `title` keyword provides a user friendly label for the property, to be displayed in a user interface instead of the technical property name. The title should be chosen to match the wording used in documentation, especially in prosa text (as opposed to configuration examples).

Example:

```json
{
  ...
  "properties": {
    "name": {
        "type": "string",
        "title": "Cluster name",
        ...
    }
  }
}
```

Additional requirements apply to the title value:

- The title MUST be written using sentence case capitalization. Correct: "Cluster name", incorrect: "Cluster Name".
- The title MUST NOT contain punctuation marks, leading or trailing white space, control characters, tabs, nor multiple whitespaces in a row.
- If the title annotates a property that is part of another object, the title SHOULD NOT include the parent property name, to avoid repetition.
  - Example: with an object `/controlPlane` that is titled `Control plane`, the property  `/controlPlane/availabilityZones` should be titled `Availability zones`, not `Control plane availability zones`.

### R6: Properties should have descriptions {#r6}

Each property SHOULD be annotated and via the `description` keyword.

Example:

```json
{
  ...
  "properties": {
    "name": {
        "type": "string",
        "description": "Identifies this cluster uniquely within the installation.",
        ...
    }
  }
}
```

If a description is given, additional requirements apply to the value:

- Description content MUST NOT include any line breaks.
- Descriptions MUST NOT contain formatting code like e.g. Markdown or HTML, leading or trailing white space, control characters, tabs, nor multiple whitespaces in a row.
- Descriptions MUST use sentence case capitalization and punctuation.
- The description SHOULD NOT repeat the property name or title. Correct: "Identifies this cluster uniquely within the installation.", incorrect: "Cluster name identifies this cluster uniquely within the installation.".
- Descriptions SHOULD be between 50 and 200 characters long.
- Descriptions SHOULD be written in simple language.

### R7: Some properties should provide examples {#r7}

Properties of type `string` SHOULD provide at least one value example using the `examples` keyword, if the property is restricted either using `pattern` or `format`.

Example:

```json
{
  ...
  "properties": {
    "name": {
        "type": "string",
        "pattern": "^[a-z0-9]{5,10}$",
        "examples": ["devel001"],
        ...
    }
  }
}
```

An example can give users easy-to-understand guidance on how to use a property. Ideally, examples SHOULD be valid cases, fulfilling the constraints of the property (if given).

Multiple examples can be provided. Additional examples should only be provided to indicate the range of different values possible. There SHOULD NOT be more than five examples per property.

### R8: Constrain values as much as possible {#r8}

Property schema SHOULD explicitly restrict values as much as possible.

There are several ways this requirement can/has to be fulfilled, depending on the property type and the use case.

String properties SHOULD be constrained by at least one of the keywords `const`, `enum`, `pattern`, `minLength`, or `maxLength`, or `format`.

Numeric properties (type `number`, `integer`) SHOULD be constrained by at least one of the keywords `minimum` or `exclusiveMinimum`, `maximum` or `exclusiveMaximum`.

Example:

```json
"diskSizeInGb": {
  "type": "integer",
  "minimum": 10,
  "maximum": 200,
  "multipleOf": 10
}
```

### R9: Required properties {#r9}

If a property is required to be set by the creator of a cluster, it MUST be included in the `required` keyword.

Properties that have default values defined in the app's `values.yaml` file MUST NOT be set as required, as here the default values are applied in case no user value is given.

Properties that get default values assigned via some external mechanism (e.g. an admission controller) also MUST NOT be set as required. An example here would be the name of a cluster or node pool, where a unique name would be generated in case none is given.

Note: If property of type object named `a` has required properties, this does not indicate that `a` itself must be defined in the instance. However it indicates that if `a` is defined, the required properties must be defined, too.

### R10: Use `anyOf` and `oneOf` only for specific purposes {#r10}

The keywords `anyOf` and `oneOf` allow definition of multiple subschemas, where the payload must match the constraints of either one (`oneOf`) or any number of (`anyOf`) subschemas. For user interface generation, this creates great complications, hence we strongly restrict the use of these features.

A cluster app MAY only make use of the `anyOf` or `oneOf` keyword in the following ways:

1. to specify validation constraints via subschemas
2. to declare one or more subschemas as deprecated

#### (1) Specifying validation constraints via subschemas

The idea here is that each subschema only defines constraints for the validation of the payload.

In this case, the subschemas MUST NOT contain any of the following keywords:

- `type` declaration
- annotations (`title`, `description`, `examples`)
- `properties`, `patternProperties`, `additionalProperties`
- `items`, `additionalItems`

The following examples shows a string property with two subschemas, where each one has a different validation pattern.

```json
"diskSize": {
  "type": "string",
  "title": "Volume size",
  "examples": ["10 GB", "10000 MB"],
  "oneOf": [
    {
      "pattern": "^[0-9]+ GB$"
    },
    {
      "pattern": "^[0-9]+ MB$"
    }
  ]
}
```

#### (2) Declaring a subschema as deprecated

If the schema of a property changes over time, while keeping the name of the property, the use of subschemas in combination with the `deprecated` keyword can help phase out an old schema and introduce a new one.

As an exception to the rules defined in (1) above, the subschemas MAY use the JSON Schema keywords forbidden under (1) if `"deprecated": true` is present in all except one of the subschemas.

In the case of a generated user interface, only the non-deprecated subschema will be applied. All other subschemas will be ignored.

Example:

```json
"replicas": {
  "anyOf": [
    {
      "type": "string",
      "deprecated": true,
      "$comment": "to be removed in the next major version, please use the integer type instead"
    },
    {
      "type": "integer",
      "maximum": 100,
      "title": "Size"
    }
  ]
}
```

## R11: Use `deprecated` to phase out properties {#r11}

To indicate that a property is supposed to be removed in a future version, the property SHOULD carry the `deprecated` key with the value `true`.

As a consequence, user interfaces for cluster creation SHALL NOT display the according form field for data entry. However, providing the property within values YAML will not cause any failure.

In addition, it is RECOMMENDED to add a `$comment` key to the property, with information regarding

- which property will replace the deprecated one (if any)
- when the property will be removed

Note that `$comment` content is not intended for display in any UI nor processing in any tool. It is mainly targeting schema developers and anyone using the schema itself as a source of information.

## R12: Provide valid string values where possible {#r12}

For string properties, in some cases only a few values are considered valid. In this case, the schema SHOULD specify these selectable values in one of the following forms:

1. Using `enum` in case the selectable value does not require a more user-friendly label.
2. Using `oneOf` with a combination of `title` and `const`, in case a user-friendly label is needed in addition to the value. See below for more details.

As an example of the `enum` method, we use a string property with two possible values. The values `active` and `inactive` are considered to be speaking for themselves.

```json
"autoRefresh": {
  "type": "string",
  "title": "Auto refresh",
  "enum": ["active", "inactive"]
}
```

However, if the string values are not considered self-explanatory, the `oneOf` method can be used to provide user-friendly labels in addition to the axctual value. Here, `oneOf` is an array of tuples, in which `title` contains the user-friendly description and `const` provides the value.

```json
"imagePullPolicy": {
  "type": "string",
  "title": "Pull policy",
  "description": "Whether the container image should be pulled from a registry",
  "oneOf": [
    {"const": "IfNotPresent", "title": "Pull image if not present in the node"},
    {"const": "Always", "title": "Always pull up-to-date image"},
    {"const": "Never", "title": "Never pull image, use image available locally"}
  ]
}
```

### R13: Avoid recursion {#r13}

The JSON Schema keywords `dynamicRef`, `dynamicAnchor`, and `recursiveRef` MUST NOT be used.

### R14: Avoid logical constructs using `if`, `then`, `else` {#r14}

The JSON Schema keywords `if`, `then`, and `else` MUST NOT be used.

### R15: Avoid `unevaluatedProperties`, `unevaluatedItems` {#r15}

The JSON Schema keywords `unevaluatedProperties` , `unevaluatedItems` MUST NOT be used.

### R16: Array items and tuple validation {#r16}

All array items MUST be of the same type.

The JSON Schema keywords `contains`, `additionalItems` and `prefixItems` MUST NOT be used.

### R17: Common schema structure {#r17}

For cluster apps, we aim to use a common schema structure among the providers we support. This structure accounts for the necessary differences that can occur between providers, as some concepts and implementations are provider-specific.

Each cluster app values schema MUST offer the following root level properties:

| Property name | Property type | Description |
|-|-|-|
| `metadata` | object | Descriptive settings like name, description, cluster labels (e. g. service priority), owner organization |
| `connectivity` | object | Settings related to connectivity and networking, and defining how the cluster reaches the outside world and how it can be reached. |
| `controlPlane` | object | Configuration of the cluster's control plane, Etcd, API server and more. |
| `nodePools` | array or object | Configuration of node pools (groups of worker nodes), regardless of their implentation flavour. |

In addition, the cluster app values schema SHOULD offer the following root level properties:

| Property name | Property type | Description |
|-|-|-|
| `internal` | object | Settings which are not supposed to be configured by end users, and which won't be exposed via user interfaces. Also experimental features that undergo schema changes. |
| `providerSpecific` | object | Configuration specific to the infrastructure provider. |

For compatibility reasons, the schema MAY have the following properties in the root level:

- `managementCluster`
- `baseDomain`
- `provider`
- `cluster-shared`
- `defaultMachinePools`
- `kubectlImage`

The schema MUST NOT define any other properties on the root level, in addition to the ones mentioned above.

### R18: Avoid using empty values in defaults {#r18}

If a property specifies a default via the default keyword, then the default MUST not be an empty value.

The definition of an empty value differs by type.
| type    | empty value                           |
|---------|---------------------------------------|
| Boolean | `false`                               |
| String  | `""`                                  |
| Integer | `0`                                   |
| Number  | `0` or everthing that's equal (`0.0`) |
| Array   | `[]`                                  |
| Object  | `{}`                                  |

## TODO

I haven't gotten to these yet, or I'm not sure about them.

- Should schemas have the `$id` property defined? And if yes, to what?

- Use of the `default` keyword. As per JSON Schema documentation, it is for annotation only. It is not meant to automatically fill in missing values for validation.

- How to specify whether a property can be modified or not. `"readOnly": true` mit be the right one for that.

- Clarify use of `Not`.

- dependentRequired, dependentSchemas: to be evaluated.

- contentEncoding in combination with contentSchema: to be defined.
  - see "username:password" in base 64 example

## Resources

- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
