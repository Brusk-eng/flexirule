# Security Architecture

FlexiRule implements a multi-layered security model to protect the system from unauthorized rule execution and arbitrary code execution.

## 1. Access Control & Role-Based Permissions

FlexiRule uses Frappe's role system to control access at multiple levels.

### Administrative Access
*   **DocType Permissions**: Standard Frappe permissions on `Rule`, `Process`, and `Rule Scheduler`.
*   **Rule Builder Role**: Required to access the visual Rule Builder and save rules.
*   **System Manager Role**: Bypasses most internal FlexiRule permission checks.

### Execution Permissions
*   **`skip_for_roles`**: A blacklist of roles that are explicitly prevented from triggering a rule.
*   **`permissions` Table**: A granular whitelist within a `Rule` defining which roles `can_execute`.
*   **`require_builder_access`**: A gate in `flexirule/ruleflow/core/permissions.py` used by all whitelisted API endpoints.

## 2. Secure Execution Environment

### SafeFrappeAPI
The `SafeFrappeAPI` (in `flexirule/ruleflow/core/engine.py`) is a restricted proxy of the standard `frappe` object.
*   **Read-Only Operations**: Only allows `get_value`, `get_all`, `db_exists`, etc.
*   **Prohibited Operations**: `get_doc`, `new_doc`, `save`, `db_set_value`, and `sql` are explicitly blocked.
*   **Usage**: This proxy is injected into the `safe_eval` context for all rule trigger conditions.

### ReadOnlyDocument
When executing rules in a "Pure" or highly restricted context, the engine wraps the subject document in a `ReadOnlyDocument` proxy that raises a `ValidationError` on any attempt to mutate fields or call save methods.

### `safe_eval` & Expression Compilation
*   **Compilation**: Trigger conditions are compiled into Python expressions on save.
*   **Validation**: `validate_safe_eval` checks expressions for forbidden patterns before they are saved.
*   **Context Control**: No dangerous built-ins (like `__import__` or `eval`) are provided to the evaluation context.

## 3. Extensibility Security

### Process Namespace Filtering
`check_method_permission` enforces that only methods within allowed namespaces (defaulting to `flexirule.*`) can be executed. This prevents calling arbitrary Python functions via the `Process` action.

### Skip Permissions Audit
If a `Rule Action` is configured to `skip_permissions`, the system:
1.  Verifies the user has the `System Manager` role (by default).
2.  Requires a mandatory `permission_audit_reason`.
3.  Logs a warning to the security log.

## 4. Resource Protection

*   **Execution Timeouts**: `max_execution_time` (configured per rule) uses a `time_limit` context manager to prevent runaway rules from hanging the server.
*   **Recursion Guards**: `RuleCoordinator` uses a request-local re-entry stack to detect and stop infinite recursion of rule triggers.

## Runtime Usage Verification

| Security Control | Status | Verification |
| :--- | :--- | :--- |
| `SafeFrappeAPI` | **Active** | Injected in `RuleCoordinator.check_eligibility`. |
| `require_builder_access`| **Active** | Called in `api.py` and `Process` controller. |
| `check_rule_permission` | **Active** | Called in `RuleEngine._validate_execution`. |
| `max_execution_time` | **Active** | Enforced via `time_limit` in `RuleEngine.execute`. |
| `Namespace Filter` | **Active** | `check_method_permission` called during Process resolution. |

## Threat Model Observations
*   **Trust Boundary**: The primary trust boundary is the **Rule Builder**. Anyone with "Rule Builder" access can potentially write complex Python expressions that, while restricted, could still be used for denial-of-service (e.g., very slow queries) or information disclosure via permitted `frappe.get_value` calls.
*   **User Input**: User-controlled inputs in documents (`doc.field`) are available in the evaluation context. These are treated as data, but if used inside a `value_template` (Jinja), they are rendered. FlexiRule relies on Frappe's Jinja security (which is generally robust) to prevent SSTI.
*   **`frappe.db.set_value`**: The `Batch Database Set` mutation mode bypasses DocType `validate()` hooks and permission checks. Access to this mode should be strictly controlled via `Process` policies.
