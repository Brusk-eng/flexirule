import frappe
from flexirule.ruleflow.process.enrichment.enrichment import set_value, calculate_value


def test_enrichment():
    # Create a mock doc
    doc = frappe.new_doc("ToDo")
    doc.description = "Test Task"
    doc.allocated_to = "test@example.com"

    context = {"doc": doc}

    # Test Jinja set_value
    print("Testing set_value with Jinja...")
    set_value(
        context,
        {
            "field": "description",
            "value": "Task for {{ doc.allocated_to }} on {{ today() }}",
            "overwrite": 1,
        },
    )
    print(f"Result: {doc.description}")
    assert "test@example.com" in doc.description
    assert str(frappe.utils.today()) in doc.description

    # Test calculate_value
    print("Testing calculate_value...")
    doc = frappe.new_doc("Quotation Item")  # Just for fields
    doc.qty = 10
    doc.rate = 5
    context = {"doc": doc}

    calculate_value(
        context, {"target_field": "amount", "formula": "doc.qty * doc.rate"}
    )
    print(f"Result: {doc.amount}")
    assert doc.amount == 50

    print("Enrichment tests passed!")


if __name__ == "__main__":
    frappe.connect(site="insight.test")
    try:
        test_enrichment()
    finally:
        frappe.destroy()
