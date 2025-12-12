# FlexiRule

![FlexiRule Logo](flexiRule.png)

## Enterprise-Grade Rule Engine & Data Quality Framework for Frappe / ERPNext

FlexiRule is a fully extensible, no-code / low-code rule engine designed to replace hard-coded business logic in ERPNext.  
Instead of embedding conditions and validations inside Python hooks, FlexiRule allows you to define **Rules**, **Actions**, and **Process Methods** that execute dynamically based on document events.

This project represents the evolution of **UPH → Business Rule Hub → Bolton → FlexiRule**, now offering a cleaner, standardized, and scalable architecture.

---

## 🚀 Key Features

- **Graph-Based Execution**  
  Build complex logic flows using a graph of rule actions.

- **Process Methods**  
  Pluggable functional units written in Python and fully configurable via JSON schemas.

- **No-Code Configuration**  
  The UI auto-generates configuration forms based on each method’s schema.

- **Data Quality Tools**  
  Built-in deduplication (fuzzy / exact matching), normalization, and child-table scanning.

- **Safe Execution**  
  Timeout-controlled execution with centralized error handling.

- **Extensible Architecture**  
  Easily add or extend Process Methods without changing core logic.

---

## 🏗️ Architecture

FlexiRule is built around three core DocTypes:

1. **Rule**  
   Defines the trigger DocType, event, and optional filters.

2. **Rule Action**  
   Represents a single step in the execution graph and links to a Process Method.

3. **Process Method**  
   A Python function that performs logic and exposes a configuration schema.

```mermaid
graph LR
    Trigger[Rule Trigger]
    --> Action1[Action: Validate]
    Action1 -->|Success| Action2[Action: Check Duplicates]
    Action1 -->|Fail| Stop[Stop Execution]
    Action2 -->|Found| Action3[Action: Block Save]
    Action2 -->|None| Action4[Action: Enrich Data]