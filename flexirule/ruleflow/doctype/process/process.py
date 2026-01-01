# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt
import datetime
import json
import threading
import os
import frappe
from frappe import _, cstr, scrub
from frappe.model.document import Document
from frappe.modules import get_app_publisher, get_module_path
from frappe.modules.export_file import export_to_files
from frappe.utils import now_datetime


class Process(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from flexirule.ruleflow.doctype.process_operation.process_operation import ProcessOperation
        from frappe.types import DF

        default_ref_doctype: DF.Link | None
        is_standard: DF.Literal["No", "Yes"]
        module: DF.Link
        operations: DF.Table[ProcessOperation]
        process_name: DF.Data
    # end: auto-generated types

 
    def validate(self):
        """Ensure module is set (same as Report)."""
        if not self.module:
            self.module = frappe.db.get_value("DocType", self.default_ref_doctype, "module")

        if not self.is_standard:
            self.is_standard = "No"
            if (
                frappe.session.user == "Administrator"
                and getattr(frappe.local.conf, "developer_mode", 0) == 1
            ):
                self.is_standard = "Yes"
        funcs = []
        for op in self.operations:
            if op.func_name in funcs:
                frappe.throw(_("Operation {0} is defined multiple times").format(op.func_name))
            funcs.append(op.func_name)
    def on_update(self):
        """Export files in developer_mode (same as Report)."""
        self.export_doc()

    def after_insert(self):
        """Create boilerplate files in developer_mode."""
        self.export_doc()

    
    def export_doc(self):
        if frappe.flags.in_import:
            return

        if self.is_standard == "Yes" and frappe.conf.developer_mode:
            export_to_files(
                record_list=[["Process", self.name]],
                record_module=self.module,
                create_init=True,
            )
            self.create_process_files()

    def create_process_files(self):
        """
        Create controller.py and controller.js using Process-specific templates.
        """
        make_process_boilerplate("controller.py", self)
        make_process_boilerplate("controller.js", self)


def make_process_boilerplate(template, doc):

    # Target path: {app}/{module}/process/{name}/
    module_path = get_module_path(doc.module)
    target_path = os.path.join(module_path, "process", scrub(doc.name))
    
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    template_name = template.replace("controller", scrub(doc.name))
    target_file_path = os.path.join(target_path, template_name)

    # Template path: flexirule/ruleflow/doctype/process/boilerplate/
    template_file_path = frappe.get_app_path(
        "flexirule", "ruleflow", "doctype", "process", "boilerplate", template
    )

    if os.path.exists(target_file_path):
        return

    app_publisher = get_app_publisher(doc.module)

    with open(target_file_path, "w") as target, open(template_file_path) as source:
        content = source.read()
        rendered_content = cstr(content).format(
            app_publisher=app_publisher,
            year=now_datetime().year,
            classname=doc.name.replace(" ", "").replace("-", ""),
            name=doc.name,
        )
        target.write(frappe.as_unicode(rendered_content))

   
    def execute(self, context,func=None,config=None):
        """
        Execute the process.
        Entry point equivalent to Report.get_data().
        """
        return self.execute_module(context,func,config)

    def execute_module(self, context,func=None,config=None):
        """
        Execute file-backed process module.
        Mirrors Report.execute_module().
        """
        method_path = (
            get_process_module_dotted_path(self.module, self.name) + ".execute"
        )
        return frappe.get_attr(method_path)(context, func,config)

   
    def get_operation(self, func_name):
        """
        Return enabled operation row by func_name.
        """
        for op in self.operations:
            if op.func_name == func_name:
                if not op.enabled:
                    frappe.throw(
                        _("Operation {0} is disabled").format(func_name)
                    )
                return op

        frappe.throw(
            _("Operation {0} not found in process {1}").format(
                func_name, self.name
            )
        )


def get_process_module_dotted_path(module, process_name):
    """
    Mirrors get_report_module_dotted_path() exactly.

    Convention:
    {app}.{module}.process.{process_name}.{process_name}
    """
    processname=frappe.scrub(process_name)
    return (
        frappe.local.module_app[frappe.scrub(module)]
        + "."
        + frappe.scrub(module)
        + ".process."
        + processname
        + "."
        + processname
    )


@frappe.whitelist()
def get_process_js_paths():
    """
    Return JS adapter paths for all processes.
    Same idea as Report JS loading.
    """
    processes = frappe.get_all("Process", fields=["name", "module"])
    result = {}

    for proc in processes:
        scrubbed = frappe.scrub(proc.name)
        app = frappe.local.module_app.get(frappe.scrub(proc.module))
        if not app:
            continue

        result[proc.name] = (
            f"/assets/{app}/{frappe.scrub(proc.module)}/process/"
            f"{scrubbed}/{scrubbed}.js"
        )

    return result
