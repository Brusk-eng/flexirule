# Salesforce Flow to FlexiRule Reference: Error Handling Patterns

Robust error handling is critical for mission-critical automation. This document describes how Salesforce handles flow errors and how FlexiRule should adapt these concepts.

## 1. Fault Paths (Try/Catch)

**Description:**
Salesforce allows connecting an alternate line (Fault Connector) from elements that perform Database actions (Create, Update, Delete) or Action calls. If an error occurs (e.g., locking issue, validation rule failure), the flow proceeds down the Fault Path instead of failing outright.

**Example:**
A flow attempts to update an Account. If a validation rule fails the DML operation, the Fault Path triggers an email alert to the admin with `{!$Flow.FaultMessage}` and logs a custom error record.

**Mapping to FlexiRule:**
- **Counterpart:** `Error Path` / `Try-Catch Node` logic.
- **Implementation:** In the Vue Flow canvas, certain nodes (like Action nodes firing Server Scripts or Document Updates) should support an `on_error` edge/connector.
- **Backend Mechanics:** The Execution Engine wraps node execution in a `try...except` block. If an exception occurs and an error path exists, it catches the exception, injects `sys.error_message` into the context, and routes to the error adjacent node. If no error edge exists, the Rule Execution fails.

## 2. Pause and Rollback

**Description:**
In Salesforce Screen flows, users have "Previous" buttons, but DML limits and transactions are committed at specific boundaries. A Rollback Records element explicitly undoes previous database changes made within the current transaction if an error occurs.

**Example:**
A flow creates an Opportunity and multiple Opportunity Line Items. If the 3rd line item fails to create, the Rollback Records element undoes the creation of the Opportunity and other successful line items.

**Mapping to FlexiRule:**
- **Counterpart:** Frappe Database Transactions (`frappe.db.rollback()`).
- **Implementation:** 
  - Since Record-Triggered FlexiRules map to Frappe hooks, they share the hook's database transaction. An uncaught exception natively rolls back the entire standard Frappe transaction.
  - For complex flows, consider a `Rollback Node` that explicitly calls `frappe.db.rollback()` but keeps the flow execution logging alive.

## 3. Standard UI Error Display

**Description:**
Salesforce shows red, cryptic "UNHANDLED FAULT" pages to users if a screen flow fails without a fault path. Admins receive automated emails with debug logs.

**Mapping to FlexiRule:**
- **Counterpart:** Frappe `frappe.msgprint()`, `frappe.throw()`, and Error Logs.
- **Implementation:** 
  - Ensure unhandled rule errors raise `frappe.throw()` to halt the UI when necessary.
  - FlexiRule generates a `Rule Execution Log` automatically for failures, recording the Node Id, Stack Trace, and active Context JSON.

## 4. Debugging and Testing Interfaces

**Description:**
Salesforce provides a "Debug" canvas allowing admins to run the flow AS a specific user, input variables, and view a granular right-hand trace of every database query and assignment.

**Mapping to FlexiRule:**
- **Implementation Goal:** Develop a "Run Mock Rule" interface or "Debug Mode" in the FlexiRule Rule Builder. It should simulate the event trigger (passing a test Doctype ID), execute the engine synchronously, and output a node-by-node execution trace highlighting the path taken on the Vue Flow canvas.
