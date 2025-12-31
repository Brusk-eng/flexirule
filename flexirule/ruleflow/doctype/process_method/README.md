# Developer Note:
## Supported FieldType for Config Schema and method resolving value
Beside all fieldtype that provided by frappe framework, we also support some custom fieldtype:
- DocField : To pick field from document type accept options to fetch pointer to target Doctype.
- MultiFieldPicker : To pick multiple fields from document type accept options to fetch pointer to target Doctype.
- MultiSelectList : To pick multiple values from list accept Static list of options or options to fetch pointer to target Doctype.
- MultiSelect : To pick multiple values from list accept Static list of options or options to fetch pointer to target Doctype.
### ChildTable :
    To add a Child Table : the child table must be reference by name even if it did not exist in frappe doctype 
    and childtable must be added to child_tables :
    ```
     "fields": [
            {
                "fieldname": "overall_threshold",
                "fieldtype": "Float",
                "label": "Overall Threshold",
                "default": 0.8,
                "description": "Minimum weighted similarity score (0-1)"
            },
            {
                "fieldname": "minimum_fields_matched",
                "fieldtype": "Int",
                "label": "Min Fields to Match",
                "default": 1
            },
            {
                "fieldname": "stop_after_first_match",
                "fieldtype": "Check",
                "label": "Stop After First Match",
                "default": 0
            },
            {
                "fieldname": "fields_config",
                "fieldtype": "Table",
                "label": "Field Comparison Rules",
                "reqd": 1,
                "options": "Dedupe Field Config"
            }
        ],
        "child_tables": {
            "Dedupe Field Config": [
                {
                    "fieldname": "fieldname",
                    "fieldtype": "DocField",
                    "label": "Field",
                    "reqd": 1,
                    "options": "parent.document_type"
                },
                {
                    "fieldname": "algorithm",
                    "fieldtype": "Select",
                    "label": "Algorithm",
                    "options": "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
                    "reqd": 1,
                    "default": "Fuzzy"
                },
                {
                    "fieldname": "weight",
                    "fieldtype": "Float",
                    "label": "Weight",
                    "default": 0.2,
                    "precision": 2
                },
                {
                    "fieldname": "threshold",
                    "fieldtype": "Float",
                    "label": "Threshold",
                    "default": 0.8,
                    "precision": 2,
                    "description": "Min score for this field (0-1)"
                },
                {
                    "fieldname": "tolerance",
                    "fieldtype": "Int",
                    "label": "Tolerance",
                    "default": 30,
                    "description": "For Date Distance: +/- days. For Numeric Range: % difference"
                },
                {
                    "fieldname": "normalize",
                    "fieldtype": "Check",
                    "label": "Normalize",
                    "default": 1
                },
                {
                    "fieldname": "included_in_filters",
                    "fieldtype": "Check",
                    "label": "Use for Blocking",
                    "default": 1,
                    "description": "Use this field in initial candidate filtering"
                }
            ]
        }
        ```
    