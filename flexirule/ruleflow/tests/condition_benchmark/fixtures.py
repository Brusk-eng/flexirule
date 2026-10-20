# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import frappe


@dataclass
class BenchmarkFixture:
	"""Represents a benchmark test fixture case."""

	fixture_id: str
	tier: str
	description: str
	condition_payload: Any
	matching_doc: Any
	non_matching_doc: Any
	expected_matching_result: bool = True
	expected_non_matching_result: bool = False
	leaf_count: int = 1
	nesting_depth: int = 1


def get_all_fixtures() -> list[BenchmarkFixture]:
	"""Return standard benchmark fixture corpus across all complexity tiers."""
	fixtures = []

	# --- Tier 1: Simple Condition ---
	tier1 = BenchmarkFixture(
		fixture_id="tier1_simple_equality",
		tier="Tier 1 — Simple",
		description="Single leaf comparison for status equality",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Open"},
				}
			],
		},
		matching_doc=frappe._dict({"status": "Open", "doctype": "ToDo"}),
		non_matching_doc=frappe._dict({"status": "Closed", "doctype": "ToDo"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(tier1)

	# --- Tier 2: Typical Business Rule ---
	tier2 = BenchmarkFixture(
		fixture_id="tier2_typical_business_rule",
		tier="Tier 2 — Typical Business Rule",
		description="Three leaf conditions joined by AND",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Submitted"},
				},
				{
					"left": {"ref": "doc.grand_total"},
					"op": ">",
					"right": {"value": 1000},
				},
				{
					"left": {"ref": "doc.customer_group"},
					"op": "==",
					"right": {"value": "Commercial"},
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 1500,
				"customer_group": "Commercial",
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 800,
				"customer_group": "Commercial",
				"doctype": "Sales Order",
			}
		),
		leaf_count=3,
		nesting_depth=1,
	)
	fixtures.append(tier2)

	# --- Tier 3: Nested AND/OR Groups ---
	tier3 = BenchmarkFixture(
		fixture_id="tier3_nested_and_or_groups",
		tier="Tier 3 — Nested Groups",
		description="Nested AND/OR groups for status and total/priority",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.status"},
							"op": "==",
							"right": {"value": "Draft"},
						},
						{
							"left": {"ref": "doc.status"},
							"op": "==",
							"right": {"value": "Submitted"},
						},
					],
				},
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.grand_total"},
							"op": ">=",
							"right": {"value": 5000},
						},
						{
							"left": {"ref": "doc.priority"},
							"op": "==",
							"right": {"value": "High"},
						},
					],
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 6000,
				"priority": "Medium",
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Cancelled",
				"grand_total": 6000,
				"priority": "High",
				"doctype": "Sales Order",
			}
		),
		leaf_count=4,
		nesting_depth=2,
	)
	fixtures.append(tier3)

	# --- Tier 4: Deep Nested Complex Rule ---
	tier4 = BenchmarkFixture(
		fixture_id="tier4_deep_nested_complex",
		tier="Tier 4 — Deep Nested Complex",
		description="10 leaf conditions across 3 nested levels with mixed operators",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.docstatus"},
					"op": "==",
					"right": {"value": 1},
				},
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.territory"},
							"op": "in",
							"right": {"value": ["North", "East", "West"]},
						},
						{
							"left": {"ref": "doc.is_prime_customer"},
							"op": "==",
							"right": {"value": 1},
						},
					],
				},
				{
					"op": "and",
					"conditions": [
						{
							"left": {"ref": "doc.net_amount"},
							"op": ">",
							"right": {"value": 500},
						},
						{
							"left": {"ref": "doc.discount_percentage"},
							"op": "<=",
							"right": {"value": 15},
						},
						{
							"op": "or",
							"conditions": [
								{
									"left": {"ref": "doc.workflow_state"},
									"op": "==",
									"right": {"value": "Approved"},
								},
								{
									"left": {"ref": "doc.auto_approved"},
									"op": "==",
									"right": {"value": 1},
								},
							],
						},
					],
				},
				{
					"left": {"ref": "doc.notes"},
					"op": "is_set",
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"docstatus": 1,
				"territory": "North",
				"is_prime_customer": 0,
				"net_amount": 750,
				"discount_percentage": 10,
				"workflow_state": "Approved",
				"auto_approved": 0,
				"notes": "Verified rule context",
				"doctype": "Sales Invoice",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"docstatus": 1,
				"territory": "South",
				"is_prime_customer": 0,
				"net_amount": 750,
				"discount_percentage": 10,
				"workflow_state": "Approved",
				"auto_approved": 0,
				"notes": "Verified rule context",
				"doctype": "Sales Invoice",
			}
		),
		leaf_count=8,
		nesting_depth=3,
	)
	fixtures.append(tier4)

	# --- Tier 5: Collection Child Records ---
	tier5 = BenchmarkFixture(
		fixture_id="tier5_collection_child_records",
		tier="Tier 5 — Collection / Child Records",
		description="Collection condition checking items child table with 'any' logic",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Submitted"},
				},
				{
					"collection": "doc.items",
					"op": "any",
					"alias": "item",
					"where": {
						"op": "and",
						"conditions": [
							{
								"left": {"ref": "item.qty"},
								"op": ">",
								"right": {"value": 10},
							},
							{
								"left": {"ref": "item.rate"},
								"op": ">=",
								"right": {"value": 100},
							},
						],
					},
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"items": [
					frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
					frappe._dict({"item_code": "ITEM-2", "qty": 15, "rate": 120}),
				],
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"items": [
					frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
					frappe._dict({"item_code": "ITEM-2", "qty": 8, "rate": 120}),
				],
				"doctype": "Sales Order",
			}
		),
		leaf_count=3,
		nesting_depth=2,
	)
	fixtures.append(tier5)

	# --- Edge Case: Null vs Empty String ---
	edge1 = BenchmarkFixture(
		fixture_id="edge_case_is_set_null_empty",
		tier="Edge Case — Null / Empty",
		description="Checking is_set with null vs empty string vs non-empty string",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.remarks"},
					"op": "is_set",
				}
			],
		},
		matching_doc=frappe._dict({"remarks": "Some notes"}),
		non_matching_doc=frappe._dict({"remarks": ""}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge1)

	# --- Edge Case: Link Tuple ---
	edge2 = BenchmarkFixture(
		fixture_id="edge_case_link_tuple",
		tier="Edge Case — Link Tuple",
		description="Link tuple comparison for Customer link field",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.customer"},
					"op": "==",
					"right": {"value": ["Customer", "CUST-00001"]},
				}
			],
		},
		matching_doc=frappe._dict({"customer": "CUST-00001"}),
		non_matching_doc=frappe._dict({"customer": "CUST-00002"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge2)

	return fixtures
