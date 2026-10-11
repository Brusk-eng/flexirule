# Child-Table Aggregation Capability Audit in Fetch Records

**Target Repository:** `Sendipad/flexirule`
**Related UI PR:** [#389 — Compact Syntax-Aware Output Fields Editor](https://github.com/Sendipad/flexirule/pull/389)
**Framework:** Frappe v15 (MariaDB 10.6+ / MySQL 8.0+)
**Branch under Audit:** `feat/fetch-records-mode`
**Audit Scope:** Analysis-only capability audit backed by executable Frappe v15 bench tests.

---

## 1. Executive Verdict

| Audit Question | Verdict | Summary |
| :--- | :---: | :--- |
| **1. Is child-table aggregation possible in Frappe v15?** | **YES** | Native PyPika query terms with explicit `LEFT JOIN` clauses on child DocTypes execute cleanly and accurately in Frappe v15. |
| **2. Is it supported by raw dotted field strings in `frappe.qb.get_query`?** | **NO** | `frappe.qb.get_query` string field parser fails to detect child tables wrapped inside function calls (e.g. `sum(items.qty)`), omitting the required `LEFT JOIN` and raising MariaDB `OperationalError 1054`. |
| **3. Is it supported by the current FlexiRule Fetch Records implementation?** | **NO** | `QueryRecordsHandler._fetch_records` passes raw field string expressions directly to `frappe.qb.get_query`, causing runtime database errors whenever a child-table field is passed inside an aggregate function. |
| **4. Can it be supported safely with a bounded extension to the query compiler?** | **YES** | A structured query compiler can build explicit PyPika child joins, apply strict `parent`, `parenttype`, and `parentfield` join constraints, auto-manage `GROUP BY` clauses, enforce a single-child-table rule (preventing Cartesian product inflation), and preserve Frappe's permission contract. |

---

## 2. Empirical Evidence & Executable Test Results

All test cases were executed against the live MariaDB-backed test site (`test_site`) in the installed Frappe v15 bench environment (`/home/jules/frappe-bench`).

### 2.1 Test Environment & Fixture Setup

- **Test Doctypes:** `QB Test Parent` (Parent) and `QB Test Child` (Child Table field `items`).
- **Fixture Records:**
  - **P1 (`l87s1atjte`):** Enabled = 1, Status = "Open", 3 child rows (`ITEM-001` qty=2 rate=10, `ITEM-001` qty=3 rate=10, `ITEM-002` qty=5 rate=20). Total Qty = 10.0.
  - **P2 (`l875vqoa6g`):** Enabled = 1, Status = "Pending", 1 child row (`ITEM-001` qty=1 rate=10). Total Qty = 1.0.
  - **P3 (`l87o5sin6t`):** Enabled = 0, Status = "Closed", 0 child rows (empty collection).

### 2.2 Raw Dotted String Aggregation in `frappe.qb.get_query`

Passing raw aggregate string expressions containing child-table dots (`items.qty`, `items.rate`, `items.name`) to `frappe.qb.get_query` produces the following results:

| Expression Configured | Generated SQL | Observed Execution Result |
| :--- | :--- | :--- |
| `sum(items.qty) as res` | `SELECT name, SUM(items.qty) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")` |
| `count(items.name) as res` | `SELECT name, COUNT(items.name) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.name' in 'SELECT'")` |
| `avg(items.rate) as res` | `SELECT name, AVG(items.rate) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |
| `min(items.rate) as res` | `SELECT name, MIN(items.rate) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |
| `max(items.rate) as res` | `SELECT name, MAX(items.rate) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |

### 2.3 Fetch Records Handler Execution Trace

Executing `QueryRecordsHandler._fetch_records` with action configuration:
```json
{
  "operation": "Fetch Records",
  "reference_doctype": "QB Test Parent",
  "config": {
    "fields": ["name", "sum(items.qty) as total_qty"],
    "group_by": "name"
  }
}
```
**Output Exception Trace:**
```text
pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")
```
*Confirmation:* `QueryRecordsHandler._fetch_records` does not transform or compile aggregate function strings before delegating to `frappe.qb.get_query`.

---

## 3. Detailed Aggregation Semantics Audit (Use Cases A–E)

### Use Case A: Aggregate Child Rows Per Parent

**Objective:** Calculate aggregate values (`SUM`, `COUNT`, `AVG`, `MIN`, `MAX`) for each parent record.

**PyPika Implementation:**
```python
parent_tbl = frappe.qb.DocType("QB Test Parent")
child_tbl = frappe.qb.DocType("QB Test Child")

query = (
    frappe.qb.from_(parent_tbl)
    .left_join(child_tbl)
    .on(
        (child_tbl.parent == parent_tbl.name)
        & (child_tbl.parenttype == "QB Test Parent")
        & (child_tbl.parentfield == "items")
    )
    .select(
        parent_tbl.name,
        Sum(child_tbl.qty).as_("total_qty"),
        Count(child_tbl.name).as_("item_count"),
        Avg(child_tbl.rate).as_("avg_rate"),
        Min(child_tbl.rate).as_("min_rate"),
        Max(child_tbl.rate).as_("max_rate"),
    )
    .groupby(parent_tbl.name)
)
```

**Compiled SQL:**
```sql
SELECT
  `tabQB Test Parent`.`name`,
  SUM(`tabQB Test Child`.`qty`) `total_qty`,
  COUNT(`tabQB Test Child`.`name`) `item_count`,
  AVG(`tabQB Test Child`.`rate`) `avg_rate`,
  MIN(`tabQB Test Child`.`rate`) `min_rate`,
  MAX(`tabQB Test Child`.`rate`) `max_rate`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name`
 AND `tabQB Test Child`.`parenttype` = 'QB Test Parent'
 AND `tabQB Test Child`.`parentfield` = 'items'
GROUP BY `tabQB Test Parent`.`name`
```

**Verified Results:**
- **P1 (`l87s1atjte`):** `total_qty=10.0`, `item_count=3`, `avg_rate=13.3333`, `min_rate=10.0`, `max_rate=20.0`.
- **P2 (`l875vqoa6g`):** `total_qty=1.0`, `item_count=1`, `avg_rate=10.0`, `min_rate=10.0`, `max_rate=10.0`.
- **P3 (`l87o5sin6t`):** `total_qty=None`, `item_count=0`, `avg_rate=None`, `min_rate=None`, `max_rate=None`.

*Key Takeaway:* Left joins correctly return `0` for `COUNT` and `None` (`NULL`) for `SUM`/`AVG`/`MIN`/`MAX` when child collections are empty.

---

### Use Case B: Aggregate Across All Matching Child Rows (Global Aggregation)

**Objective:** Compute a single summary row across all matching child rows without grouping by parent.

**PyPika Implementation:**
```python
query = (
    frappe.qb.from_(parent_tbl)
    .left_join(child_tbl)
    .on(
        (child_tbl.parent == parent_tbl.name)
        & (child_tbl.parenttype == "QB Test Parent")
        & (child_tbl.parentfield == "items")
    )
    .where(parent_tbl.enabled == 1)
    .select(
        Sum(child_tbl.qty).as_("global_qty"),
        Count(child_tbl.name).as_("global_count"),
        Avg(child_tbl.rate).as_("global_avg"),
    )
)
```

**Compiled SQL:**
```sql
SELECT
  SUM(`tabQB Test Child`.`qty`) `global_qty`,
  COUNT(`tabQB Test Child`.`name`) `global_count`,
  AVG(`tabQB Test Child`.`rate`) `global_avg`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name`
 AND `tabQB Test Child`.`parenttype` = 'QB Test Parent'
 AND `tabQB Test Child`.`parentfield` = 'items'
WHERE `tabQB Test Parent`.`enabled` = 1
```

**Verified Results:** `[{'global_qty': 11.0, 'global_count': 4, 'global_avg': 12.5}]` (Exactly 1 global summary row returned).

---

### Use Case C: Mixed Parent Fields and Child Aggregates (`ONLY_FULL_GROUP_BY`)

**Objective:** Verify SQL compliance when non-aggregated parent fields (`status`, `parent_title`) are selected alongside child aggregates.

**Tested Grouping Options:**

1. **Group by Primary Key (`parent.name`):**
   ```sql
   SELECT `tabQB Test Parent`.`name`, `tabQB Test Parent`.`status`, `tabQB Test Parent`.`parent_title`, SUM(`tabQB Test Child`.`qty`) `total_qty`
   FROM `tabQB Test Parent`
   LEFT JOIN `tabQB Test Child` ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name` ...
   GROUP BY `tabQB Test Parent`.`name`
   ```
   *Execution Result:* **SUCCESS.** Under MariaDB / MySQL `ONLY_FULL_GROUP_BY`, grouping by the primary key `name` guarantees functional dependency of all other parent columns (`status`, `parent_title`), so MariaDB executes this query without error.

2. **Group by All Non-Aggregated Selected Columns:**
   ```sql
   GROUP BY `tabQB Test Parent`.`name`, `tabQB Test Parent`.`status`, `tabQB Test Parent`.`parent_title`
   ```
   *Execution Result:* **SUCCESS.** Guarantees strict SQL-92/99 compatibility across all SQL engines.

---

### Use Case D: Multiple Child Tables & Cartesian Join Inflation

**Objective:** Test join semantics and numeric correctness when a parent DocType joins multiple child tables simultaneously.

**Experimental Setup:**
Parent P1 has **3 rows** in `QB Test Child` (qty: 2, 3, 5 -> true sum = 10.0) and **2 rows** in `QB Test Child 2` (scores: 10, 20 -> true sum = 30.0).

**Compiled Multi-Child Query:**
```sql
SELECT
  `tabQB Test Parent`.`name`,
  SUM(`tabQB Test Child`.`qty`) `total_qty`,
  COUNT(`tabQB Test Child`.`name`) `item_count`,
  SUM(`tabQB Test Child 2`.`score`) `total_score`,
  COUNT(`tabQB Test Child 2`.`name`) `comment_count`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name` AND `tabQB Test Child`.`parenttype` = 'QB Test Parent' AND `tabQB Test Child`.`parentfield` = 'items'
LEFT JOIN `tabQB Test Child 2`
  ON `tabQB Test Child 2`.`parent` = `tabQB Test Parent`.`name` AND `tabQB Test Child 2`.`parenttype` = 'QB Test Parent' AND `tabQB Test Child 2`.`parentfield` = 'comments'
WHERE `tabQB Test Parent`.`name` = 'l87s1atjte'
GROUP BY `tabQB Test Parent`.`name`
```

**Observed Results Comparison:**

| Metric | Single Child Join Expected | Multi-Child Join Actual | Multiplication Factor |
| :--- | :---: | :---: | :---: |
| `total_qty` | **10.0** | **20.0** | **2x** (multiplied by 2 child2 rows) |
| `item_count` | **3** | **6** | **2x** |
| `total_score` | **30** | **90** | **3x** (multiplied by 3 child1 rows) |
| `comment_count` | **2** | **6** | **3x** |

**Critical Architectural Finding:** Joining multiple child tables in a single flat SQL query creates a Cartesian product ($3 \times 2 = 6$ intermediate joined rows). Aggregate functions (`SUM`, `COUNT`, `AVG`) compute over these duplicate rows and produce **corrupted, inflated aggregate values**!

*Design Mandate:* FlexiRule must explicitly **reject queries that attempt to aggregate over multiple child tables in a single query**, or compile child aggregations into separate CTEs / subqueries before joining.

---

### Use Case E: Permissions & Security Contract

**Objective:** Ensure query execution preserves Frappe's security contract and row-level permissions.

**Execution Audit:**
- `execute_query(doctype, kwargs, ignore_permissions=False)` checks session permissions via Frappe's `Permission.check_permissions(query, user)`.
- When executed under a restricted user context (e.g. `Guest`), `execute_query` correctly enforces permission checks and raises `PermissionError`.
- Any bounded query compiler extension must pass its constructed PyPika query through `Permission.check_permissions(query, user)` or attach `DatabaseQuery(doctype).build_match_conditions()`.

---

## 4. Capability Matrix

| Aggregate Function | Input Syntax Mode | Grouping Mode | Frappe v15 Engine Support | Current Fetch Records Support | Root Cause of Failure / Status |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | Dotted String (e.g. `sum(items.qty)`) | Per-Parent / Global | **NO** | **UNSUPPORTED** | Engine string parser fails to detect child table inside function call; missing `LEFT JOIN`. |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | PyPika Term + Explicit Join | Per-Parent (`GROUP BY parent`) | **YES** | **UNSUPPORTED** | `frappe.qb.get_query` interface does not accept PyPika join objects via `kwargs`. |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | PyPika Term + Explicit Join | Global (No `GROUP BY`) | **YES** | **UNSUPPORTED** | Requires custom PyPika builder. |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | Multi-Child Table Join | Any | **DANGEROUS** | **UNSUPPORTED** | Causes Cartesian product row inflation ($N \times M$), producing invalid aggregate numbers. |

---

## 5. Failure Analysis

### Exact Failure Location & Root Cause

1. **Location:** `frappe/database/query.py` -> `Engine._parse_field` / `Engine._get_fields_from_string`.
2. **Mechanism:**
   - When a plain field string like `"items.qty"` is passed, `Engine._parse_field` splits on `.` and registers a child table `LEFT JOIN` on `tabQB Test Child`.
   - When a function-wrapped string like `"sum(items.qty) as total_qty"` is passed, `Engine._parse_field` matches the function regex (e.g. `sum(...)`), wraps the inner string directly into a PyPika `CustomFunction` or `Sum` term, but **skips table field path inspection** for the inner argument.
   - The compiled SQL contains `SUM(\`items.qty\`)` or `SUM(\`items\`.\`qty\`)`, but **no `LEFT JOIN` clause** is added to the `FROM` block.
3. **Database Error:**
   - MariaDB receives `SELECT name, SUM(items.qty) res FROM tabQB Test Parent GROUP BY name`.
   - MariaDB throws: `pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")`.

---

## 6. Recommended Design Options & Architecture

### Option Comparison

| Option | Engineering Effort | Maintenance Cost | Risk | Recommendation |
| :--- | :---: | :---: | :---: | :--- |
| **Option 1: Retain String Expressions Only** | Zero | Zero | None | Keep current behavior (reject child aggregates in UI). |
| **Option 2: Structured Child-Table Aggregation Compiler** | Medium | Low | Low | **RECOMMENDED FOR FUTURE ENHANCEMENT.** Build a dedicated compiler helper that detects aggregate functions over child fields, constructs explicit PyPika `LEFT JOIN`s, enforces single-child-table boundaries, auto-generates `GROUP BY`, and enforces permissions. |
| **Option 3: Fallback to `frappe.get_list`** | High | High | High | Not recommended; `frappe.get_list` lacks Query Builder term flexibility and pagination controls. |

### Proposed Bounded Compiler Architecture (Option 2)

If FlexiRule chooses to implement child-table aggregation in a future release, the architecture must follow these strict rules:

```text
Configured Fields ["name", "sum(items.qty) as total_qty"]
                   │
                   ▼
     ┌───────────────────────────┐
     │  FlexiRule Query Compiler │
     └─────────────┬─────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ 1. Validate Single Child Table
    │ 2. Build PyPika Parent DocType Term
    │ 3. Build PyPika Child DocType Term
    │ 4. Add ON (child.parent==parent.name AND parenttype AND parentfield)
    │ 5. Wrap Field in PyPika Sum/Count/Avg/Min/Max
    │ 6. Auto-add non-aggregated fields to GROUP BY
    │ 7. Apply Permission.check_permissions(query, user)
    └──────────────┬──────────────┘
                   │
                   ▼
         Native PyPika Query Execution
```

**Mandatory Guardrails for the Compiler:**
1. **Single Child Table Rule:** Reject any query configuration that attempts to aggregate fields from more than one child table in the same query to prevent Cartesian multiplication.
2. **Strict Join Condition:** Always include `child.parent == parent.name`, `child.parenttype == parent_doctype`, and `child.parentfield == child_fieldname`.
3. **`GROUP BY` Auto-Completion:** Automatically add all selected non-aggregate parent fields to the `GROUP BY` clause to comply with `ONLY_FULL_GROUP_BY`.
4. **Permissions:** Execute `Permission.check_permissions(query, user)` prior to `query.run()`.

---

## 7. Test Plan for Future Feature Implementation

Before enabling child-table aggregation in Fetch Records, the following test suite must be implemented and passing:

1. **Single Child Table Aggregation Tests (`test_fetch_records_child_aggregation.py`):**
   - Test `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` per parent on a child table.
   - Verify empty child collection handling (returns `0` for count, `None`/`NULL` for sums/averages).
2. **Global Aggregation Tests:**
   - Test global summary queries across all matching child rows without `GROUP BY`.
3. **Multi-Child Table Prevention Test:**
   - Assert that configuring fields from two distinct child tables in an aggregate query raises a validation error: `"Child-table aggregation supports only one child table per query to prevent data duplication."`
4. **`GROUP BY` Compliance Test:**
   - Test queries selecting `parent.name`, `parent.status`, and `SUM(items.qty)` to verify proper `GROUP BY` compilation.
5. **Security & Permission Tests:**
   - Execute child aggregate queries as a non-System Manager user and verify that permission restrictions on parent documents are strictly enforced.
6. **Regression Suite:**
   - Execute full existing `test_fetch_records.py` and `test_frappe_qb_capabilities.py` suites to ensure zero regressions for non-aggregate queries.

---

## 8. UI Recommendation for PR #389

Based on the empirical evidence gathered during this audit:

1. **Retain Current Restriction in `output_fields_model.js`:**
   PR #389 currently includes the following validation in `validateOutputFields`:
   ```javascript
   if (field.includes(".")) {
     errors.push(
       prefix +
       "aggregate functions currently support root DocType fields only; child/link aggregates need backend support."
     );
   }
   ```
   **Verdict:** This validation rule is **100% CORRECT and NECESSARY**. It accurately reflects the capabilities of the current backend. Removing this restriction without backend compiler changes would allow users to save configurations that crash at runtime with MariaDB `OperationalError 1054`.

2. **Conditions for Lifting the UI Restriction:**
   The UI validation restriction in `output_fields_model.js` should remain in place until:
   - A structured child-table query compiler is implemented in `flexirule/ruleflow/core/action_handlers/query_records.py`.
   - The backend integration test suite specified in Section 7 is fully implemented and passing in CI.

---

## 9. Final Capability Verdict & Summary

- **Child-Table Aggregation via Raw Dotted Strings:** **UNSUPPORTED** (Fails at DB execution with MariaDB Error 1054).
- **Child-Table Aggregation via PyPika Explicit Joins:** **POSSIBLE & VERIFIED** (Supported natively by Frappe v15 / PyPika).
- **Current Fetch Records Mode:** **UNSUPPORTED** (Delegates directly to raw string parser).
- **Recommended Action for PR #389:** **RETAIN CURRENT UI RESTRICTION** (Block aggregate source fields containing dots).
