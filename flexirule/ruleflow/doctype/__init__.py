# TODO : if frappe respect creating table on installing new app based on fields order in json files then reorder fields in json files based on their important 
# TODO : Delete empty Folder

"""
TODO: for data_quality_issue,data_quality_record,data_review_related_document,data_reviewer must apply below:
confirm its naming (doctype naming) , should we keep them or merge them into better named Doctype to be usefull for the following use case as unified Doctype that could be used for mdm tasks:
since my app do provide some mdm methods @flexirule/methods/ then there should be some methods that will be responsible for creating a task .
This task must have its created by 'rule' link a copy of context when created 
a reference doctype and docname , and list of related effected/effected_by docname and doctype
a process_method link fieldtype for suggested method if provided to be executed to mark the task as resolved and another fields of input parameters to be used as arguments for the suggested method
if there provided process_method then a button must open dialog with input parameters as visual and if required more parameters 
all other fields that required.
"""