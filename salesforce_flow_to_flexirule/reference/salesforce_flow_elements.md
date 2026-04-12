# Salesforce Flow Elements

## Interaction Elements

### Screen

- Presents forms to users for data input and display
- Supports various input types: text, number, date, picklist, etc.
- Can include sections, headers, and footers
- Available only in Screen Flows

### Action

- Executes predefined actions such as sending emails, creating records, or calling external services
- Includes standard actions and custom Apex actions
- Can pass data to and receive data from actions

### Subflow

- Calls another Flow within the current Flow
- Enables modular design and reusability
- Supports parameter passing between flows

## Logic Elements

### Decision

- Evaluates conditions to determine flow path
- Supports multiple outcomes based on criteria
- Can use AND/OR logic for complex conditions

### Assignment

- Sets values to variables or record fields
- Supports direct assignments and formula-based calculations
- Can manipulate collections and individual records

### Transform

- Maps data from one structure to another
- Useful for converting between different data formats
- Supports complex data transformations

### Filter

- Reduces collection size by applying criteria
- More efficient than processing all records in loops
- Can filter based on multiple conditions

### Sort

- Orders collection items based on specified fields
- Supports ascending/descending order
- Can sort by multiple fields with priorities

### Loop

- Processes collections item by item
- Supports nested loops for complex hierarchies
- Essential for bulk operations

## Data Elements

### Get Records

- Retrieves records from Salesforce objects
- Supports SOQL queries with filters and sorting
- Can get single records or collections

### Create Records

- Inserts new records into Salesforce objects
- Supports bulk creation for efficiency
- Can set all required and optional fields

### Update Records

- Modifies existing records
- Supports bulk updates
- Can update single records or collections

### Delete Records

- Removes records from Salesforce
- Supports bulk deletion
- Includes safety checks and permissions

## Additional Elements

### Start

- Entry point for all flows
- Can include input parameters for triggered flows

### End

- Termination point for flows
- Can include output parameters for subflows
