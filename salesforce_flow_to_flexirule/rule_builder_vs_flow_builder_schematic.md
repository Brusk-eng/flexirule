# Visual Schematic: Rule Builder vs Flow Builder Architecture

## Interface Layout Schematic

```
┌─────────────────────────────────────────────────────────────────┐
│                    SALESFORCE FLOW BUILDER                      │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────────────┐ ┌─────────────────────┐         │
│ │ Toolbox │ │     Canvas      │ │   Properties        │         │
│ │         │ │                 │ │                     │         │
│ │ ◇ Start │ │ ┌─────────────┐ │ │ ◇ General           │         │
│ │ ◇ Screen│ │ │  Element 1  │ │ │ ◇ Advanced          │         │
│ │ ◇ Action│ │ │             │ │ │ ◇ Validation        │         │
│ │ ◇ Loop  │ │ └─────────────┘ │ │                     │         │
│ │ ◇ ...   │ │       │         │ └─────────────────────┘         │
│ └─────────┘ │ ┌─────────────┐ │                                 │
│              │ │  Element 2  │ │ ┌─────────────────────┐         │
│              │ │             │ │ │     Errors          │         │
│              │ └─────────────┘ │ │ ○ Warning: ...      │         │
│              │       │         │ │ ○ Error: ...        │         │
│              │ ┌─────────────┐ │ └─────────────────────┘         │
│              └─┤   Element 3  ├─┘                                 │
│                │             │                                   │
│                └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     FLEXIRULE RULE BUILDER                      │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────────────────────────────────────┐         │
│ │ Actions │ │              Node Graph                │         │
│ │         │ │                                         │         │
│ │ ◯ Cond. │ │     ◯───────▶ ◯───────▶ ◯              │         │
│ │ ◯ Loop  │ │    Start    Action 1   Action 2         │         │
│ │ ◯ Set   │ │                                         │         │
│ │ ◯ Query │ │     │         │         │               │         │
│ │ ◯ ...   │ │     ▼         ▼         ▼               │         │
│ └─────────┘ │     ◯         ◯         ◯               │         │
│              │   True     False     Next              │         │
│              └─────────────────────────────────────────┘         │
│                                                                 │
│ ┌─────────────────────────────────────────────────────┐         │
│ │                 Action Configuration                │         │
│ │                                                     │         │
│ │ Action Type: Set Value                             │         │
│ │ Target Variable: doc.status                        │         │
│ │ Value: "Approved"                                  │         │
│ │                                                     │         │
│ └─────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Element/Action Comparison Matrix

```
FLOW BUILDER ELEMENTS                    RULE BUILDER ACTIONS
═══════════════════════════════════    ═════════════════════════════════
◇ Screen Flow                         ◯ Entry Action
  └─ User Interface                     └─ Rule Initialization

◇ Record-Triggered Flow               ◯ Condition
  └─ Database Event                      └─ Conditional Execution

◇ Autolaunched Flow                   ◯ Sub Rule
  └─ Background Process                  └─ Modular Execution

◇ Decision Element                    ◯ Switch
  └─ Multi-outcome Branching            └─ Multi-case Branching

◇ Loop Element                        ◯ Loop
  └─ Collection Iteration               └─ Context Iteration

◇ Get Records                         ◯ Query Records
  └─ SOQL Query Builder                 └─ Flexible Database Query

◇ Update Records                      ◯ Create Doc
  └─ DML Operations                     └─ Document Creation

◇ Transform                          ◯ Set Value
  └─ Data Mapping                       └─ Variable Assignment

◇ Wait/Pause                         ◯ Stop
  └─ Time-based Delay                  └─ Execution Termination

◇ Send Email                         ◯ Notify
  └─ Email Integration                 └─ User Notifications

◇ Subflow                            ◯ Process Operation
  └─ Reusable Components               └─ Higher-level Operations
```

## Data Flow Visualization

```
SALESFORCE FLOW DATA FLOW:
═════════════════════════

Record Trigger → Get Related Data → Decision Logic → Data Transform → Update Records
      │                │                    │              │              │
   ┌──▼──┐          ┌──▼──┐              ┌──▼──┐        ┌──▼──┐        ┌──▼──┐
   │ Doc  │          │Query│              │Logic│        │ Map │        │Save │
   │Data  │          │Data │              │Rules│        │Data │        │Data │
   └──────┘          └─────┘              └─────┘        └─────┘        └─────┘

FLEXIRULE DATA FLOW:
═══════════════════

Rule Trigger → Context Setup → Action Processing → Result Mapping → Final State
      │            │               │                │              │
   ┌──▼──┐      ┌──▼──┐         ┌──▼──┐         ┌──▼──┐       ┌──▼──┐
   │Input │      │Vars │         │Exec │         │Map  │       │Out  │
   │Data  │      │Store│         │Logic│         │Data │       │State│
   └──────┘      └─────┘         └─────┘         └─────┘       └─────┘
```

## Feature Comparison Grid

```
FEATURE CATEGORY     │ SALESFORCE FLOW BUILDER │ FLEXIRULE RULE BUILDER
═════════════════════╪═════════════════════════╪════════════════════════
Visual Interface     │ Element-based canvas    │ Node-graph visualization
                     │ Drag-and-drop elements  │ Interactive node editor
                     │ Property panels         │ Dynamic configuration

Data Handling        │ Record variables        │ Context variables
                     │ Collection processing   │ Array/list operations
                     │ SOQL queries            │ Flexible query builders
                     │ Transform mapping       │ Variable assignments

Logic & Flow         │ Decision branching      │ Conditional execution
                     │ Loop iteration          │ Context iteration
                     │ Subflow calls           │ Sub-rule execution
                     │ Error handling          │ Exception management

User Interaction     │ Rich screen components  │ Basic notifications
                     │ Form validation         │ User feedback
                     │ Navigation controls     │ External forms
                     │ Reactive updates        │ Limited interactivity

Extensibility        │ Apex actions            │ Python handlers
                     │ Custom LWCs             │ Custom Vue components
                     │ AppExchange solutions   │ Modular action system
                     │ Platform APIs           │ Frappe integrations

Debugging & Testing  │ Debug panel             │ Execution tracing
                     │ Rollback mode           │ Context inspection
                     │ Variable inspection     │ Performance metrics
                     │ Error highlighting      │ Test execution mode

Performance & Scale  │ Governor limits         │ Configurable timeouts
                     │ Bulk operations         │ Efficient algorithms
                     │ Platform optimization   │ Resource monitoring
                     │ Async processing        │ Background execution

Security & Governance│ Platform security       │ Safe execution context
                     │ Permission sets         │ Role-based access
                     │ Audit trails            │ Execution logging
                     │ Data validation         │ Type checking
```

## Architecture Comparison Diagram

```
SALESFORCE FLOW ARCHITECTURE:
═══════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                    SALESFORCE PLATFORM                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │             FLOW BUILDER UI                         │    │
│  │  ┌─────────┐ ┌────────────┐ ┌─────────────────┐     │    │
│  │  │ Toolbox │ │   Canvas  │ │  Properties     │     │    │
│  │  └─────────┘ └────────────┘ └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │            FLOW EXECUTION ENGINE                    │    │
│  │  ┌─────────┐ ┌────────────┐ ┌─────────────────┐     │    │
│  │  │Elements │ │Interpretor│ │Governor Limits  │     │    │
│  │  └─────────┘ └────────────┘ └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    DATABASE & APIs                          │
└─────────────────────────────────────────────────────────────┘

FLEXIRULE ARCHITECTURE:
══════════════════════

┌─────────────────────────────────────────────────────────────┐
│                  FRAPPE FRAMEWORK                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │            RULE BUILDER UI                          │    │
│  │  ┌─────────┐ ┌────────────┐ ┌─────────────────┐     │    │
│  │  │Actions  │ │Node Graph │ │Configuration    │     │    │
│  │  └─────────┘ └────────────┘ └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │            RULE EXECUTION ENGINE                    │    │
│  │  ┌─────────┐ ┌────────────┐ ┌─────────────────┐     │    │
│  │  │Handlers │ │Engine     │ │Safe Context     │     │    │
│  │  └─────────┘ └────────────┘ └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                 PYTHON & DATABASE                           │
└─────────────────────────────────────────────────────────────┘
```

## User Experience Workflow Comparison

```
CREATING A SIMPLE APPROVAL RULE:

SALESFORCE FLOW BUILDER:
1. Create new Flow → Select Record-Triggered
2. Configure trigger: Object = Opportunity, Event = Update
3. Add Entry Criteria: Status = "Pending Approval"
4. Add Decision: Check Amount > 10000
5. Add Screen (if needed): Approval Form
6. Add Update Records: Set Status = "Approved"
7. Save and Activate

FLEXIRULE RULE BUILDER:
1. Create new Rule → Select trigger type
2. Configure trigger: Doctype = "Opportunity", Event = "on_update"
3. Add Condition: Check doc.status == "Pending Approval"
4. Add Condition: Check doc.amount > 10000
5. Add Set Value: doc.status = "Approved"
6. Save and Test
```

## Performance Characteristics

```
METRIC                     │ SALESFORCE FLOW          │ FLEXIRULE
═══════════════════════════╪══════════════════════════╪════════════════════════════
Execution Time             │ Platform dependent       │ Configurable (30s default)
Memory Usage               │ Governor limited         │ Framework dependent
Concurrent Users           │ Multi-tenant shared      │ Single-tenant dedicated
Database Queries           │ SOQL governor limits     │ Direct database access
External Calls             │ HTTP governor limits     │ Python network limits
File Storage               │ Salesforce storage       │ Server filesystem
Caching Strategy           │ Platform caching         │ Redis/application cache
Error Recovery             │ Limited rollback         │ Transaction management
Monitoring                 │ Platform logs            │ Application logs
Scaling                    │ Horizontal platform      │ Vertical server scaling
```

## Integration Capabilities

```
EXTERNAL SYSTEMS           │ SALESFORCE FLOW          │ FLEXIRULE
═══════════════════════════╪══════════════════════════╪════════════════════════════
REST APIs                  │ HTTP Callouts            │ Python requests library
Database                   │ SOQL/SOSL queries        │ Direct SQL connections
Email Systems              │ Send Email action        │ SMTP integrations
File Storage               │ Salesforce Files         │ Local/S3/cloud storage
Message Queues             │ Platform Events          │ Redis/Celery queues
Authentication             │ Named Credentials        │ OAuth/API keys
Third-party Apps           │ AppExchange connectors  │ Python SDKs/libraries
Legacy Systems             │ Apex integrations        │ Custom Python adapters
Real-time Updates          │ Streaming API            │ WebSocket integrations
Batch Processing           │ Scheduled Flows          │ Cron job integration
```

This schematic comparison illustrates the fundamental architectural and visual differences between the two systems while highlighting their complementary strengths and potential areas for feature cross-pollination.
