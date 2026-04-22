# Salesforce Flow to FlexiRule Reference: Node Types and Behaviors

## Salesforce Setup: Flow Elements (Nodes)

Salesforce Flow Elements dictate the logic within a flow. They are grouped into Interaction, Logic, and Data.

### 1. Data Elements (Create, Update, Get, Delete Records)
**Description:** Performs DML (Database Manipulation Language) operations. 
**Example:** "Get Records" fetches child Contacts matching an Account ID. "Update Records" applies changes to the trigger document.

**Mapping to FlexiRule:**
- **Action Node (Rule Action):** Needs specialized Action Types maping to Database CRUD.
- **Example in Frappe:** `frappe.get_doc()`, `frappe.get_all()`, `doc.save()`, `doc.delete()`.
- FlexiRule should categorize Rule Actions as `Data Actions`.

### 2. Logic Elements (Assignment)
**Description:** Assigns values to variables, record fields, or collections locally within the flow execution memory state without committing to the database.

**Mapping to FlexiRule:**
- **Action Node (Variable Assignment):** Maps to assigning properties to `doc.field` or storing contextual keys in the FlexiRule execution `context`.

### 3. Logic Elements (Decision)
**Description:** Evaluates criteria and branches out the execution paths based on evaluated outcomes. Allows multiple outgoing paths.

**Mapping to FlexiRule:**
- **Condition Node / Switch Node:** FlexiRule maps this to a `Rule Condition` node. Like Salesforce, it must allow logical branching. Currently FlexiRule often supports True/False or Switch (Multi-path). The UI should clearly show branching arrows.

### 4. Logic Elements (Loop)
**Description:** Iterates over a collection (array) of records or values.

**Mapping to FlexiRule:**
- **Loop Node:** Uses standard Python iteration on arrays stored in context. For each item, the logic branches into the "For Each" path, returning to the Loop node when done.

### 5. Interaction Elements (Action, Subflow, Email)
**Description:** Calling standard/custom Apex logic, sending alerts, or triggering nested flows.

**Mapping to FlexiRule:**
- **Sub-Rule Node:** For nested rule graphs.
- **Notification Node (System Action):** For Email, SMS, or internal Frappe Alerts.
- **Custom Script (Server Script Action):** Code Execution mapping directly to custom Server Scripts.
