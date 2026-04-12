# Salesforce Flow to FlexiRule Reference: Subflows and Reusability

This document details how Salesforce Flow handles subflows and reusability, and how these patterns can be implemented in FlexiRule's architecture.

## 1. Subflows (Autolaunched Flows)

**Description:**
A Subflow element calls another flow. The called flow must be an autolaunched flow. Subflows allow you to break down complex logic into smaller, reusable flows. When a main flow executes a Subflow element, it pauses and waits for the subflow to finish running.

**Example:**
A standard error logging flow that takes `ErrorMessage` and `ErrorCode` as input variables, creates an Error Log record, and then returns execution to the parent flow. This flow is called as a Subflow from 10 different Record-Triggered flows.

**Mapping to FlexiRule:**
- **Counterpart:** `Sub-Rule` or `Autolaunched Rule`.
- **Implementation:** FlexiRule uses a specific `Sub-Rule Node`. When the engine hits this node, it instantiates the child Rule's execution graph.
- **Data Passing:** 
  - Subflows in Salesforce use variables marked as "Available for Input" and "Available for Output".
  - In FlexiRule, the Sub-Rule Node must map parent context variables to the child rule's expected inputs (defined as variables/arguments on the rule level). After execution, outputs from the child must be mapped back into the parent's context.
- **Execution:** The execution is synchronous. The parent execution context is suspended until the child DAG (Directed Acyclic Graph) resolves.

## 2. Global Actions and Quick Actions

**Description:**
Salesforce allows calling predefined Global Actions or Object-Specific Quick Actions (like creating a record or logging a call) directly from a flow.

**Example:**
Using a default "Log a Call" Quick Action in a flow instead of manually creating a Task record node.

**Mapping to FlexiRule:**
- **Counterpart:** `Server Scripts` / `Custom Action Nodes`.
- **Implementation:** standardizing common Frappe operations (like "Submit Document", "Cancel Document", "Assign User", "Add Comment") as reusable node templates within the `Rule Action` DocType configuration, rather than making users build them from primitive Create/Update nodes.

## 3. Invokable Methods (Apex)

**Description:**
When standard Flow elements aren't enough, Salesforce allows calling custom Apex code via `@InvocableMethod`. These methods receive a list of inputs from the flow and return a list of outputs.

**Example:**
Calling a method to make a complex REST API callout, process the JSON response, and return formatted data to the flow.

**Mapping to FlexiRule:**
- **Counterpart:** Whitelisted Python functions (`frappe.whitelist()`) or Server Scripts.
- **Implementation:** FlexiRule should provide a `Custom Code Node` or `Server Script Node` capable of calling external Python logic, passing the current context, and capturing the return payload into the flow state.

## 4. Templates

**Description:**
Salesforce allows packaging flows as internal templates. When users create a new flow, they can select a template, getting a pre-configured baseline.

**Example:**
A template for standard Customer Onboarding.

**Mapping to FlexiRule:**
- **Counterpart:** Duplicating Rules or explicitly flagging `Rule` documents as "Is Template".
- **Implementation:** Allow users to bootstrap a new Vue Flow canvas from a pre-defined JSON structure mapped to a template Rule DocType.

## Reusability Governance Impact

In Salesforce, heavily nesting Subflows could hit transaction limits (SOQL queries, CPU time).
In FlexiRule + Frappe, deep recursion or excessive database calls within nested `frappe.get_doc()` or `frappe.db.sql()` calls will impact standard request timeouts (usually 300s or 60s for Gunicorn workers). FlexiRule should eventually enforce recursion limits in the Execution Engine to prevent Infinite Loops via Sub-Rules.
