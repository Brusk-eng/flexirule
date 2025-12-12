###FlexiRule

Enterprise-Grade Rule Engine & Data Quality Framework for Frappe/ERPNext

FlexiRule is a fully extensible, no-code/low-code rule engine designed to replace hard‑coded business logic in ERPNext. Instead of embedding conditions and validations inside Python hooks, FlexiRule allows you to define Rules, Actions, and Process Methods that execute dynamically based on document events.

This release represents the evolution of UPH → Business Rule Hub → Bolton → FlexiRule, now offering a cleaner, standardized, and scalable architecture.


---

🚀 Key Features

Graph-Based Execution: Build complex logic flows using a graph of rule actions.

Process Methods: Pluggable functional units written in Python and fully configurable via JSON schemas.

No-Code Configuration: The UI auto-generates configuration forms based on each method's schema.

Data Quality Tools: Built-in deduplication (fuzzy/exact matching), field normalization, and child-table scanning.

Safe Execution: Timeout-controlled execution and sandboxing.

Extensible Architecture: Add your own Process Methods or extend existing ones.



---

🏗️ Architecture

FlexiRule centers around three core DocTypes:

1. Rule – Defines trigger DocType, event, and filters.


2. Rule Action – Represents one step in the execution graph; links to a Process Method.


3. Process Method – Python function that performs logic, with a schema describing its configuration.



graph LR
    Trigger[Rule Trigger]
    --> Action1[Action: Validate]
    Action1 -->|Success| Action2[Action: Check Duplicates]
    Action1 -->|Fail| Stop[Stop Execution]
    Action2 -->|Found| Action3[Action: Block Save]
    Action2 -->|None| Action4[Action: Enrich Data]


---

🛠️ Usage

1. Creating a Process Method (Developer)

Define a Python function and register it as a Process Method.

Python code:

# flexirule/ruleflow/methods/custom.py

def check_credit_limit(context, limit=0, **kwargs):
    doc = context.get('doc')
    if doc.grand_total > limit:
        return False
    return True

Fixture example (process_method.json):

{
  "method_path": "flexirule.ruleflow.methods.custom.check_credit_limit",
  "config_schema": "{\"fields\": [{\"fieldname\": \"limit\", \"fieldtype\": \"Currency\", \"label\": \"Max Amount\"}]}",
  "return_type": "Boolean"
}

2. Configuring a Rule (User)

Example Rule for Sales Order:

DocType: Sales Order

Event: Before Save

Action: Check Credit

Method: Check Credit Limit

Configuration: { "limit": 5000 } (form generated automatically)

Action ID: CREDIT_CHECK



3. Data Mapping (Inputs/Outputs)

FlexiRule supports dynamic variable mapping between context and method arguments.

Input Mapping:

{"customer_grade": "grade"}

Passes context['customer_grade'] → argument grade.

Output Mapping:

{"is_valid": "check_passed"}

Stores method return value → context['check_passed'].


---

📦 Contact Deduplication Example

FlexiRule ships with advanced deduplication utilities.

Scenario: Prevent saving a Contact if a phone number already exists on any other Contact.

Steps:

1. Create Rule for Contact → Before Save.


2. Add Action: Find Duplicates in Child Table.


3. Configuration:

Child Table: phone_nos

Child Field: phone



4. Add Action: Prevent Duplicate Save when duplicates are found.




---

📘 Roadmap Highlights

Standardized execution criteria for all Process Methods.

Expanded library of ready-made business logic methods.

UI improvements for the rule graph builder.

Enhanced testing utilities for rule flows.



---

🤝 Contributing

FlexiRule welcomes contributions from developers.

Open an Issue for bugs or proposals.

Submit a Pull Request with clear descriptions.

Follow existing structure and naming conventions.


See CONTRIBUTING.md for full guidelines.


---

📄 License

MIT License.


---

📬 Contact

For ideas, collaboration, or feature requests:
Open an Issue on GitHub.