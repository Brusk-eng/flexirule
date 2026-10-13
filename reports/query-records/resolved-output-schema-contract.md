# Resolved Output Schema Contract

The `Rule Action.resolved_output_schema` field describes metadata keys exposed to later actions through a return variable. Query Records generates this schema; other return-schema-enabled action types may supply it manually.

## Canonical field shape

```json
{
  "label": "Reference Doctype",
  "fieldname": "reference_doctype",
  "fieldtype": "Select",
  "options": "DocType",
  "reqd": 0,
  "source": {
    "kind": "field",
    "fieldname": "voucher_type",
    "expression": "voucher_type as reference_doctype"
  }
}
```

- `fieldname` is the actual key in the action result. For aliased queries, it is the alias rather than the input field.
- `reqd` uses Frappe's DocField property name and is normalized to integer `0` or `1`. For fields backed by DocField metadata it reflects the source field's `reqd`; generated values such as aggregate results use `0`. This is metadata, not a promise that every row has a non-null value or that the key is guaranteed at runtime.
- `source` is optional provenance for tracing, debugging, and future UI features. It must not change execution or output-key validation. Its `fieldname` refers to the source expression, not necessarily the result key.

## Source kinds

Current schema builders emit descriptive kinds including `field`, `child_field`, `child_table`, `system`, `aggregate`, `expression`, `report`, `result`, and `dynamic`. Additional kinds may be added without changing the core field metadata.

For example, an aggregate uses the alias as its output `fieldname` and stores its lineage separately:

```json
{
  "label": "Totals",
  "fieldname": "totals",
  "fieldtype": "Int",
  "reqd": 0,
  "source": {
    "kind": "aggregate",
    "function": "count",
    "fieldname": "name",
    "expression": "count(name) as totals"
  }
}
```

## Compatibility

- Updated schema producers emit `reqd`, not `mandatory`.
- The frontend canonicalizer accepts old `mandatory` values, uses them only if `reqd` is absent, and removes the legacy key from normalized schemas.
- The optional `source` object is preserved through graph load/save, manual-schema editing, and downstream variable propagation.
- Runtime return-key validation continues to examine result `fieldname` keys only; `reqd` and `source` do not change execution behavior.
