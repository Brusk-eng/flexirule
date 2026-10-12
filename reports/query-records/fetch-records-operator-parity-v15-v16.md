# Fetch Records Operator Parity Audit: Frappe 15 vs Frappe 16

**Audit date:** 2026-10-12  
**Scope:** Operators used by `frappe.qb.get_query`, which is the execution API for FlexiRule Fetch Records. This report deliberately separates Query Builder from `frappe.get_list` / `frappe.model.db_query.DatabaseQuery`; the two APIs have overlapping but non-identical parser and execution contracts.

## Executive finding

Fetch Records was not fully aligned before this audit:

1. Its backend allowlist included `<>`, but neither Frappe 15 nor Frappe 16 `OPERATOR_MAP` registers `<>`. The normal portable spelling is `!=`; Fetch Records now rejects `<>`.
2. The UI and backend must **not** expose `regex` just because the operator map contains it. Both release branches map `regex` to PyPika's `Term.regex`, which emits the SQL token `REGEX`. The inspected Frappe 15 and 16 `frappe/query_builder/utils.py` versions do not install the dialect patch that makes this executable. Frappe's `develop` source explicitly documents that `REGEX` is supported by neither backend and includes a patch mapping MariaDB/MySQL to `REGEXP` and PostgreSQL to `~*`. Since that patch was absent from both release-branch snapshots, Fetch Records now fails closed and does not advertise `regex`.
3. Frappe has five nested-set operators in both versions. The previous adapter had duplicated the list in its source; it now derives it from Frappe's `NestedSetHierarchy` constant. Backend validation now checks that a tree operator targets either the name field of a Tree DocType or a Link to a Tree DocType, rather than merely accepting the operator name.
4. The portable Fetch Records contract consists of the shared, executable filter operators, FlexiRule aliases normalized to those operators, and the five Frappe nested-set operators. Frappe 16-only or dialect-specific operators are intentionally not exposed as portable Fetch Records operators.

## Source snapshots inspected

The code below was read from both release branches, not inferred from docs or the other major version.

| Source | Frappe 15 blob SHA | Frappe 16 blob SHA | Why it matters |
|---|---|---|---|
| [`frappe/database/operator_map.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/operator_map.py) | `837d86282c4483aeec6421153123c024418f6707` | `218983a318fd8005626dffa183ea6ef54df0f120` | The Query Builder operator functions and version differences. |
| [`frappe/database/query.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/query.py) | `30318e2d79dd875b3ed9adea9d710c3c36167775` | `1377710fe5acfb1683a08eb8218e8cdae582778d` | Actual Query Builder filter parsing, operator dispatch, tree expansion and boolean filter behavior. |
| [`frappe/database/utils.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/utils.py) | `e031e8379510cf7e0121c08d1c28bbe482037297` | `9e2343538595bd822a379a24a73b1d0d865fd27d` | The canonical `NestedSetHierarchy` operator tuple. |
| [`frappe/query_builder/utils.py`](https://github.com/frappe/frappe/blob/version-15/frappe/query_builder/utils.py) | `7074321fb71d23179e2ceb7b2b147f8450a07104` | `d151133d9fb041d5b9465eca2cc8a634678149f7` | Query Builder runtime monkey patches; the checked release snapshots do not include `patch_regex_operator`. |
| [`frappe/model/db_query.py`](https://github.com/frappe/frappe/blob/version-15/frappe/model/db_query.py) | `2ddb8ee71b0526f3a4bda58574725d720b6e1cf7` | `dc0c9827703bb43260a66be0fec0dcd1aa6c8ad9` | Cross-check only. This is the ORM query path, not the Fetch Records execution path. |
| [Frappe standard filter UI `filter.js`](https://github.com/frappe/frappe/blob/version-15/frappe/public/js/frappe/ui/filters/filter.js) | `59324ff3aee40beb70c699829fd2e4c06ad26869` | `bba692739d2134a347efa6a805b3c12827f9e9f9` | Per-field operator restrictions; Frappe 16 is stricter for Select/Color comparisons and has more explicit text/numeric field rules. |

The Fetch Records UI sources inspected were [`FilterLeaf.vue`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue) and backend handler [`query_records.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/core/action_handlers/query_records.py), plus the compatibility adapter [`frappe_query_compat.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/utils/frappe_query_compat.py).

## Native Query Builder operator contract

### Operators shared by the Frappe 15 and Frappe 16 release branches

The portable executable set represented by Fetch Records is:

- Comparisons: `=`, `!=`, `<`, `<=`, `>`, `>=`.
- Pattern and membership filters: `like`, `not like`, `in`, `not in`.
- Value operators: `between`, `is`, `timespan`.
- Tree operators from `NestedSetHierarchy`: `ancestors of`, `descendants of`, `not ancestors of`, `not descendants of`, and `descendants of (inclusive)`.

Frappe's `OPERATOR_MAP` also contains `=<` and `=>`, which are aliases for `<=` and `>=`. Fetch Records uses the canonical spellings and does not offer duplicate aliases. The map also contains `+`, `-`, `/`, and `*` for expression/arithmetic operations; these are not offered as ordinary filter operators. On Frappe 15, the string `nested_set` is a registry key whose value is the tree-operator tuple, not a leaf operator; Frappe 16 imports `NESTED_SET_OPERATORS` separately. The adapter now uses the source-level `NestedSetHierarchy` constant rather than maintaining a duplicate tree list.

### Differences and important traps

| Operator or family | Frappe 15 Query Builder | Frappe 16 Query Builder | Fetch Records decision |
|---|---|---|---|
| `ilike` | Not in `OPERATOR_MAP` | In `OPERATOR_MAP`; direct SQL spelling is dialect-dependent | Not exposed in the portable contract. Frappe 16 can select ILIKE for PostgreSQL's `like` handling; MariaDB does not use the PostgreSQL ILIKE syntax. |
| `previous`, `next` | Not handled by the v15 Query Builder's simple-filter dispatch | Special-cased in `_build_criterion_for_simple_filter` and converted to date ranges | Not exposed directly because these are v16-only. The portable UI offers FlexiRule's `Timespan` abstraction, which the backend converts to `between`. |
| `regex` | Present in `OPERATOR_MAP`, but its mapped PyPika rendering is not executable on the inspected release branch | Same issue in the inspected release branch | Not exposed or allowlisted. The Frappe `develop` implementation documents the problem and adds a dialect-aware patch: [`patch_regex_operator`](https://github.com/frappe/frappe/blob/develop/frappe/query_builder/utils.py#L334-L364). PyPika's unpatched `Term.regex` emits `REGEX`, not MariaDB/MySQL's `REGEXP` or PostgreSQL's `~*` ([PyPika terms](https://github.com/kayak/pypika/blob/master/pypika/terms.py#L178-L185), [matching enum](https://github.com/kayak/pypika/blob/master/pypika/enums.py#L32-L40)). |
| `<>` | Not in `OPERATOR_MAP` | Not in `OPERATOR_MAP` | Removed from Fetch Records validation; use `!=`. |
| Custom operators from filter hooks | Not supported by this release Query Builder path | The v16 Query Builder parser consults `get_additional_filters_from_hooks()` | Not accepted in Fetch Records' fixed portable allowlist. Hook-specific operators need an explicit FlexiRule contract and frontend value/editor before they can safely be exposed. |

Do not confuse this table with `frappe.model.db_query.DatabaseQuery` or `frappe.get_list`. Those paths have their own filter conversion, including `previous`/`next` handling in Frappe 15. Fetch Records calls `frappe.qb.get_query`, so that ORM behavior does not prove that the Query Builder supports the same syntax.

## FlexiRule operator mapping after the changes

| FlexiRule UI option | Backend payload/execution | Status |
|---|---|---|
| Equals / Not Equals / relational comparisons | Native `=`, `!=`, `<`, `<=`, `>`, `>=` | Aligned on v15/v16 |
| Like / Not Like | Native `like` / `not like` | Aligned on v15/v16 |
| In / Not In | Native `in` / `not in`; the value editor provides lists/strings | Aligned on v15/v16 |
| Between | Normalized to `between` | Aligned on v15/v16 |
| Timespan | Resolved to date bounds and sent as `between` | FlexiRule abstraction, portable on v15/v16 |
| Starts With / Ends With | Normalized to `like` with a trailing/leading `%` | FlexiRule aliases; they do not pretend to be native Frappe operators |
| Is | Native `is`, with value `set` or `not set` | The backend now validates the native value contract |
| Five nested-set operators | Derived on the backend from Frappe's `NestedSetHierarchy`; adapter preserves tree behavior in standalone and boolean-group filters | Aligned on v15/v16; backend validates Tree DocType applicability |
| `<>` | Rejected | Previously accepted by the backend despite lacking a native operator mapping; corrected |
| `regex` | Rejected | Map entry is not sufficient proof of executable SQL on the inspected release branches |
| `ilike`, `previous`, `next` | Rejected by the portable allowlist | Intentionally excluded due to version/dialect differences |

The UI applies additional field-type restrictions from the Frappe standard filter UI. FlexiRule uses the **intersection of the Frappe 15 and 16 restrictions** so an operator is not offered only on one supported major version: for example, Check fields expose equality only, Select fields do not expose range comparisons (Frappe 16 adds that restriction), Color does not expose range comparisons (also stricter in v16), text-like field types follow the union of the Frappe 15/16 exclusions, and integer/numeric fields inherit the v16 numeric restrictions. `Starts With` and `Ends With` inherit the `like` restriction because they normalize to `like` in the backend.

The UI offers nested-set operators for a Link to a Tree DocType, and also for the `name` field when querying a Tree DocType. The backend validates the tree-target requirement for canonical and legacy filter shapes, so manually edited or stale configurations cannot rely solely on the UI to prevent invalid tree filters. After dynamic values resolve, the backend also checks the operator allowlist and value contracts for both canonical filter trees and older Frappe-style filter rows.

## Regression coverage added

The dedicated database-backed test module, [`test_fetch_records_tree_operators.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/tests/test_fetch_records_tree_operators.py), runs against a real persisted Tree DocType. It covers all five nested-set operators as single filters and composed with both AND and OR, plus the allowed operator set, rejected aliases/version-specific entries, `is` value validation, and Tree DocType target validation.

CI is configured with the existing full Frappe 15 backend suite and a separate Frappe 16 job that runs this integration module. CI results should be read from the current PR checks; a previous passing run does not certify this revision.

## Final assessment

Fetch Records now exposes a deliberate cross-version portable subset, not every key present in Frappe's multi-purpose `OPERATOR_MAP`. That distinction is necessary because the map includes arithmetic helpers, registry entries, version-specific filters and an operator (`regex`) that the inspected release runtime renders as invalid SQL. Operators presented in the UI now map to supported backend behavior or to an explicitly documented FlexiRule alias, and nested-set operators are checked against their target DocType rather than accepted by name alone.
