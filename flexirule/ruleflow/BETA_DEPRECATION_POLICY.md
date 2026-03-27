# FlexiRule Beta Deprecation Policy

This app is in beta. To keep changes safe and aligned with Frappe patterns, do not remove code directly without passing the checks below.

## 1. Evidence Before Removal

-   Confirm no references with repository-wide search (`rg`) across Python, JS, Vue, patches, hooks, and tests.
-   Confirm no DocType field dependency in `*.json`, controller code, and client scripts.
-   Confirm no whitelisted API or import/export dependency.

## 2. Deprecate First, Remove Later

-   Add compatibility normalization for legacy values.
-   Block new usage in UI/API where applicable.
-   Keep read compatibility for existing records during beta.

## 3. Frappe Pattern Requirements

-   Keep `DocType JSON`, server controller, and client script behavior synchronized.
-   Use data/schema patches for transitions; avoid hidden one-off mutations.
-   Preserve existing permissions and lifecycle semantics unless migration is explicit.

## 4. Validation and Tests

-   Add or update tests for every deprecation path.
-   Run targeted tests for rule validation, execution engine, and API behavior before removal.
-   Only remove deprecated paths in a later PR after passing compatibility checks.
