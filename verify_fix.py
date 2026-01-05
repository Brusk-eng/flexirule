import frappe
import os
from flexirule.ruleflow.doctype.process.process import make_process_boilerplate

def test():
    doc = frappe.get_doc({
        "doctype": "Process",
        "name": "Verification Test",
        "module": "Flexirule",
        "is_standard": "Yes"
    })
    
    # This should not raise ValueError
    try:
        make_process_boilerplate("controller.js", doc)
        print("Boilerplate JS created successfully")
        make_process_boilerplate("controller.py", doc)
        print("Boilerplate PY created successfully")
        
        # Check if files exist and contain expected values
        module_path = frappe.get_module_path(doc.module)
        target_path = os.path.join(module_path, "process", frappe.scrub(doc.name))
        js_file = os.path.join(target_path, "verification_test.js")
        
        if os.path.exists(js_file):
            with open(js_file, "r") as f:
                content = f.read()
                if 'flexirule.processes["Verification Test"]' in content:
                    print("JS Content verified")
                else:
                    print("JS Content mismatch")
                    print(content)
        else:
            print("JS File not found")

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    test()
