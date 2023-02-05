# Basic requirements for cluster app values schema

Cluster apps are apps which are used to configure and provision clusters based on Cluster API in the Giant Swarm platform. Like all helm charts, these apps are configured using so-called values YAML files, which are passed to the app as a ConfigMap for cluster creation. The allowed structure of the values YAML is defined by the app's values schema.

This RFC defines basic requirements for all cluster apps provided by Giant Swarm.

## Overview

- [R1: JSON Schema dialect (draft 2019-09) must be specified](#r1)
- [R12: A single type must be declared](#r12)
- [R2: Schema must explicitly cover all allowed properties](#r2)
- [R3: Array item schema must be defined](#r3)
- [R4: Properties must have a title](#r4)
- [R5: Properties should have descriptions](#r5)
- [R6: Properties should provide examples](#r6)
- [R7: Constrain values as much as possible](#r7)
- [R8: Required properties must be marked as such](#r8)
- [R9: Avoid `anyOf` and `oneOf`](#r9)
- [R10: Use `deprecated` to phase out properties](#r10)
- [R11: Provide valid string values where possible](#r11)
- [R13: Avoid recursion](#r13)
- [R14: Avoid logical constructs using `if`, `then`, `else`](#r14)
- [R15: Avoid `unevaluatedProperties`, `unevaluatedItems`](#r15)

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

### R1: JSON Schema dialect (draft 2019-09) must be specified {#r1}

Each cluster app's values schema file MUST specify the schema dialect (also called draft) used via the `$schema` keyword on the top level, with the draft URI as a value.

The draft URI MUST be `https://json-schema.org/draft/2019-09/schema`.

Example:

```json
{
  "$schema": "https://json-schema.org/draft/2019-09/schema",
  ...
}
```

### R12: A single type must be declared {#r12}

For each property, including the root level schema, the `type` keyword MUST be present, and there MUST be a single value for the `type` keyword.

While JSON Schema draft 2019-09 allows multiple values for the `type` keyword, for cluster-apps this would complicate the generation of user interfaces. Hence we require a single type to be specified.

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

### R2: Schema must explicitly cover all allowed properties {#r2}

All properties that can be used in values MUST be covered in the schema explicitly.

To enforce this and to disable the use of any undefined properties, the keyword `additionalProperties` SHOULD be set to `false` on all object schemas.

### R3: Array item schema must be defined {#r3}

The items schema for all array properties MUST be defined using the `items` keyword.

### R4: Properties must have a title {#r4}

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

### R5: Properties should have descriptions {#r5}

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

### R6: Properties should provide examples {#r6}

Each property SHOULD provide one or more examples using the `examples` keyword.

Example:

```json
{
  ...
  "properties": {
    "name": {
        "type": "string",
        "examples": ["devel001"],
        ...
    }
  }
}
```

An example can give users easy-to-understand guideance on how to use a property. Ideally, examples SHOULD be valid cases, fulfilling the contstraints of the property.

Multiple examples can be provided. Per property, there SHOULD be at least one example. Additional examples should only be provided to indicate the range of different values possible. There SHOULD NOT be more than five examples per property.

TODO: We could decide to use the examples for testing purposes, replacing ci-values.yaml and the likes. In that case, we should make it a MUST requirement.

### R7: Constrain values as much as possible {#r7}

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

### R8: Required properties {#r8}

If a property is required to be set by the creator of a cluster, it MUST be included in the `required` keyword.

Properties that have default values defined in the app's `values.yaml` file MUST NOT be set as required, as here the default values are applied in case no user value is given.

Properties that get default values assigned via some external mechanism (e.g. an admission controller) also MUST NOT be set as required. An example here would be the name of a cluster or node pool, where a unique name would be generated in case none is given.

Note: If property of type object named `a` has required properties, this does not indicate that `a` itself must be defined in the instance. However it indicates that if `a` is defined, the required properties must be defined, too.

### R9: Avoid `anyOf` and `oneOf` {#r9}

A cluster app schema SHALL NOT make use of the `anyOf` or `oneOf` keyword.

If using `anyOf` or `oneOf` cannot be avoided, the desired subschema SHOULD be the first in the sequence.

In JSON Schema, the `anyOf` and `oneOf` keyword defines an array of possible subschemas for a property. For a user interface which is generated based on the schema, this creates a high degree of complexity.

At Giant Swarm, our user interface for cluster creation will not support `anyOf` nor `oneOf` to full extent. Instead, we are going to select only one of the defined schemas for data input, using simply the first schema that is not deprecated.

Let's consider this example schema:

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
    },
    {...}
  ]
}
```

Here, the user interface would use the second subschema (type: integer) and ignore all others.

## R10: Use `deprecated` to phase out properties {#r10}

To indicate that a property is supposed to be removed in a future version, the property SHOULD carry the `deprecated` key with the value `true`.

As a consequence, user interfaces for cluster creation SHALL NOT display the according form field for data entry. However, providing the property within values YAML will not cause any failure.

In addition, it is RECOMMENDED to add a `$comment` key to the property, with information regarding

- which property will replace the deprecated one (if any)
- when the property will be removed

Note that `$comment` content is not intended for display in any UI nor processing in any tool. It is mainly targeting schema developers and anyone using the schema itself as a source of information.

## R11: Provide valid string values where possible {#r11}

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

## TODO

I haven't gotten to these yet, or I'm not sure about them.

- Should schemas have the `$id` property defined? And if yes, to what?

- Use of the `default` keyword. As per JSON Schema documentation, it is for annotation only. It is not meant to automatically fill in missing values for validation.

- How to specify whether a property can be modified or not. `"readOnly": true` mit be the right one for that.

- Not, AllOf, AnyOf, OneOf must only be used for constraints. No use of `type`, `properties` etc. in the sub-schema.

- DependentRequired, DependentSchemas: to be evaluated.

- AdditionalItems, PrefixItems, for tuple validation cannot be used.

- All array items must be of the same type. `contains` cannot be used.

- contentEncoding in combination with contentSchema: to be defined.
  - see "username:password" in base 64 example

## Resources

- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
