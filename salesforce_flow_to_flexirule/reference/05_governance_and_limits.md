# Salesforce Flow to FlexiRule Reference: Governance and Limits

## Framework Governance

### Salesforce Limits
Salesforce enforces strict execution limits (DML statements per transaction, SOQL queries per transaction, CPU timeout). If a flow exceeds these, it throws an uncatchable governor limit exception and rolls back the transaction. 

### Frappe/FlexiRule Limits
Frappe has different transactional controls. While Python execution timeouts exist (via Gunicorn/Worker), it doesn't have explicit SOQL count tracking per thread in the same rigorous way by default, but it does have strict recursion thresholds and database connection pool sizes.
- **Infinite Loop Protection:** The greatest risk in node-based logic networks is creating cycles. DAG graphs mathematically avoid cycles. FlexiRule execution validation must prevent cyclic dependencies.
- **Transactions & Rollback:** The `Rule Engine` in FlexiRule runs alongside `frappe.db.commit()`. If an exception occurs, Frappe rolls back the atomic transaction.
- **Deferred Execution:** Bulk loops or high-intensity processes should be offloaded using `frappe.enqueue(method)` (equivalent to Salesforce Asynchronous Processing / Future methods) rather than blocking the web thread.

## Visual Governance
The FlexiRule Frontend (Vue Builder) should enforce validation *before* saving the Rule graph. 
- If properties are omitted.
- If loose ends exist on connections.
- If cycle references exist (A -> B -> C -> A).
