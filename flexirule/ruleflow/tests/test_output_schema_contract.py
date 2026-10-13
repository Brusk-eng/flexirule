from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import _aggregate_source, _output_schema_source, _reqd_flag


class TestResolvedOutputSchemaContract(FrappeTestCase):
	def test_reqd_flag_normalizes_frappe_values(self):
		self.assertEqual(_reqd_flag(1), 1)
		self.assertEqual(_reqd_flag(True), 1)
		self.assertEqual(_reqd_flag("1"), 1)
		self.assertEqual(_reqd_flag(0), 0)
		self.assertEqual(_reqd_flag("0"), 0)
		self.assertEqual(_reqd_flag(None), 0)

	def test_aggregate_source_carries_expression_provenance(self):
		self.assertEqual(
			_aggregate_source("Count", {"field": "name"}),
			{
				"kind": "aggregate",
				"fieldname": "name",
				"expression": "count(name)",
				"function": "count",
			},
		)
		self.assertEqual(
			_aggregate_source("Count", {}),
			{"kind": "aggregate", "expression": "count(*)", "function": "count"},
		)

	def test_output_source_omits_unknown_metadata(self):
		self.assertEqual(
			_output_schema_source("field", fieldname="title", expression="title", optional=None),
			{"kind": "field", "fieldname": "title", "expression": "title"},
		)
