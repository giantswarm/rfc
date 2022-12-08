# Basic requirements for cluster app values schema

Cluster apps are apps which are used to configure and provision clusters based on Cluster API in the Giant Swarm platform. Like all helm charts, these apps are configured using so-called values YAML files, which are passed to the app as a ConfigMap for cluster creation. The allowed structure of the values YAML is defined by the app's values schema.

This RFC defines basic requirements for all cluster apps provided by Giant Swarm.

## Overview

- [R1: JSON Schema dialect must be specified](#r1)
- [R2: Schema must explicitly cover all allowed properties](#r2)
- [R3: Array item schema must be defined](#r3)
- [R4: Properties must have a title](#r4)
- [R5: Properties should have descriptions](#r5)
- [R6: Properties should provide examples](#r6)
- [R7: Constrain values as much as possible](#r7)
- [R8: Required properties must be marked as such](#r8)

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

### R1: JSON Schema dialect must be specified {#r1}

Each cluster app's values schema file MUST specify the schema dialect (also called draft) used via the `$schema` keyword on the top level, with the draft URI as a value.

Example:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  ...
}
```

The example above shows an excerpt of a JSON Schema which uses draft 2020-12.

### R2: Schema must explicitly cover all allowed properties {#r2}

All properties that can be used in values MUST be covered in the schema explicitly.

To enforce this and to disable the use of any undefined properties, the keyword `additionalProperties` SHOULD be set to `false` on all object schemas.

The `patternProperties` keyword MUST NOT be used.

### R3: Array item schema must be defined {#r3}

The items schema for all array properties MUST be defined using the `items` keyword.

### R4: Properties must have a title {#r4}

Each property MUST be annotated via the `title` keyword.

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

Rationale: These annotations (just like description and examples, see R5 and R6) are mainly useful for users during data entry, but also when reasoning about an cluster configuration.

Best practices:

- Ue sentence case.
- Do not use punctuation.
- Do not repeat the parent title.
  - Example: if `.controlPlane` is titled `Control plane`, then `.controlPlane.availabilityZones` should be titled `Availability zones`, not `Control plane availability zones`.

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

Best practices:

- Do not repeat the property name or title in the description.
- Write descriptions between 50 and 200 characters long.
- Use simple language.
- Use no formatting syntax, nor hyperlinks.
- Use no line breaks.
- Use sentence case and punctuation.

### R6: Properties should provide examples {#r6}

Each property SHOULD provide one or more examples using the `example` keyword.

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

Best practices:

- Ideally, provide one example.
- Provide more than one example if you want to highlight that very different values are accepted.
- Provide no more than five examples

TODO

- We could decide to use the examples for testing purposes, replacing ci-values.yaml and the likes. In that case, we should make it a MUST requirement.

### R7: Constrain values as much as possible {#r7}

Property schema SHOULD explicitly restrict values as much as possible.

There are several ways this requirement can/has to be fulfilled, depending on the property type and the use case.

Properties of type `string`:

- Use of the keywords `minLength` and `maxLength` to specify the valid length.
- If applicable, use the `pattern` keyword to specify a regular expression for validation. This is useful for example to restrict the value to ASCII characters, or to lowercase etc.
- Use the `format` keyword to restrict the property to a common string format, like a URL or an email address. Watch out to use only formats which are available in the JSON schema dialect used (see also R1).
- Use `enum` if only certain known values can be valid.

Numeric properties (type `number`, `integer`):

- Restrict the values range using `minimum` or `exclusiveMaximum` and `maximum` or `exclusiveMaximum`.
- Use `multipleOf` if the value has to be a multiple of a certain number.

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

## TODO

I haven't gotten to these yet, or I'm not sure about them.

- Each property must declare the `type`. Not sure this is required by JSON schema.

- Use of the `default` keyword. As per JSON Schema documentation, it is for annotation only. It is not meant to automatically fill in missing values for validation.

- How to specify whether a property can be modified or not. `"readOnly": true` mit be the right one for that.

- Use of the `deprecated` keyword to phase out properties. Documentation says: "The deprecated keyword is a boolean that indicates that the instance value the keyword applies to should not be used and may be removed in the future."

## Resources

- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
