# FlexiRule vs Salesforce Flow: Feature Comparison

This document compares FlexiRule (Frappe-based rule engine) with Salesforce Flow, highlighting similarities, differences, and potential areas for inspiration.

## Overview Comparison

| Aspect              | Salesforce Flow                           | FlexiRule                                    |
| ------------------- | ----------------------------------------- | -------------------------------------------- |
| **Platform**        | Salesforce CRM                            | Frappe Framework                             |
| **Execution Model** | Declarative visual flows                  | Graph-based rule engine with visual builder  |
| **Primary Use**     | Business process automation               | Business rule automation and workflow        |
| **Architecture**    | Flow Builder with elements and connectors | Rule Engine with actions and graph execution |
| **Deployment**      | Native Salesforce                         | Frappe app/plugin                            |
| **Extensibility**   | Apex for custom logic                     | Python action handlers                       |

## Flow Types vs Rule Types

### Salesforce Flow Types

- **Screen Flows**: Interactive user-guided processes
- **Record-Triggered Flows**: Auto-triggered on record changes
- **Autolaunched Flows**: Background processes
- **Schedule-Triggered Flows**: Time-based automation
- **Platform Event-Triggered Flows**: Event-driven

### FlexiRule Rule Types

- **Rules**: Graph-based execution with actions
- **Processes**: Higher-level operations (similar to subflows)
- **Sub-rules**: Modular rule components

**Comparison**: FlexiRule focuses on rule-based logic rather than full workflow types. Screen Flows have no direct equivalent, but interactive elements could be added.

## Elements vs Actions

### Salesforce Flow Elements

#### Interaction Elements

- **Screen**: User forms and data collection
- **Action**: Predefined operations (email, create record)
- **Subflow**: Call other flows

#### Logic Elements

- **Decision**: Conditional branching
- **Assignment**: Variable manipulation
- **Transform**: Data mapping
- **Filter**: Collection reduction
- **Sort**: Collection ordering
- **Loop**: Collection iteration

#### Data Elements

- **Get Records**: Query data
- **Create/Update/Delete Records**: CRUD operations

### FlexiRule Actions

#### Core Actions

- **Condition**: Evaluate rules and branch
- **Loop**: Iterate over collections
- **Switch**: Multi-case branching
- **Set Value**: Variable assignment
- **Stop**: End execution
- **Raise Error**: Error handling
- **Notify**: User notifications

#### Data Actions

- **Query Records**: Database queries
- **Create Doc**: Document creation
- **Process Operation**: Execute processes

#### Advanced Actions

- **Sub Rule**: Call other rules
- **Entry Action**: Rule initialization

**Comparison**: FlexiRule has fewer built-in actions but a more extensible handler system. Salesforce Flow has richer UI elements (Screen, Kanban) that FlexiRule lacks.

## Resources vs Context Variables

### Salesforce Flow Resources

- **Variables**: Text, Number, Date, Record, etc.
- **Collections**: Lists of variables
- **Constants**: Fixed values
- **Formulae**: Dynamic calculations
- **Choices**: User selection options

### FlexiRule Context

- **vars**: Dictionary for runtime variables
- **doc**: Current document being processed
- **frappe**: Safe API access
- **meta**: Execution metadata

**Comparison**: Salesforce has more structured resource types. FlexiRule uses a simpler dict-based approach but with document-centric context.

## Execution and Safety

### Salesforce Flow

- Visual canvas with auto-layout
- Governor limits (SOQL, elements)
- Debug mode with input persistence
- Flow logging and metrics

### FlexiRule

- Graph execution with cycle detection
- Timeout protection (30s default)
- Safe evaluation with restricted context
- Execution tracing and error handling

**Comparison**: Both have safety measures, but FlexiRule emphasizes security through SafeFrappeAPI and pre-compiled conditions.

## Areas for Inspiration

### High Priority

1. **Screen Components**: Add interactive UI elements like Kanban boards, data tables with inline editing
2. **Component Styling**: Allow custom styling of visual elements
3. **Debug Enhancements**: Persistent debug inputs, better error visualization
4. **Flow Navigation**: Enhanced canvas controls for large rules

### Medium Priority

1. **Advanced Data Elements**: More sophisticated data transformation actions
2. **Scheduling**: Built-in schedule-triggered rules
3. **Event Triggers**: Platform event support
4. **Metrics Dashboard**: Centralized rule performance monitoring

### Low Priority

1. **Formula Builder**: Visual formula creation (currently code-based)
2. **Template Flows**: Pre-built rule templates
3. **Version Control**: Built-in rule versioning
4. **Import/Export**: Rule migration capabilities

## Implementation Gaps

### Missing in FlexiRule

- User-interactive screens (Screen Flows)
- Visual data components (Kanban, Data Tables)
- Scheduled execution
- Platform event triggers
- Rich formula builder
- Component-level styling

### Strengths of FlexiRule

- Tighter security model
- Better performance for complex logic
- Native Frappe integration
- Extensible action system
- Document-centric execution

## Recommendations

1. **Prioritize UI Enhancements**: Add Screen-like capabilities for user interaction
2. **Expand Data Actions**: Implement more CRUD and query variations
3. **Add Visual Components**: Kanban and data table components
4. **Improve Debugging**: Persistent inputs and better visualization
5. **Consider Scheduling**: Add time-based rule triggers
6. **Enhance Monitoring**: Add execution metrics and logging

This comparison shows that while FlexiRule has a solid foundation, adopting Salesforce Flow's user experience and visual capabilities would significantly improve its usability and adoption.
