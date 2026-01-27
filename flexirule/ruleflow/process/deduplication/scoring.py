# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
ScoringEngine - Implements deduplication and fuzzy matching
Handles similarity scoring, blocking strategies, and duplicate detection
"""

import json
from typing import Any

import frappe
from rapidfuzz import fuzz, process


class ScoringEngine:
	"""
	Deduplication and similarity scoring engine
	Implements blocking strategies to reduce O(n²) comparisons
	"""

	def __init__(self, rule_doc):
		"""
		Initialize scoring engine with deduplication rule

		Args:
		        rule_doc: Rule document with type = 'Deduplication'
		"""
		self.rule = rule_doc
		self.options = json.loads(rule_doc.options_json) if rule_doc.options_json else {}
		self.threshold = self.options.get("match_threshold", 85)
		self.blocking_fields = self.options.get("blocking_fields", [])
		self.scoring_fields = self.options.get("scoring_fields", [])

	def find_duplicates(self, doc) -> list[dict]:
		"""
		Find potential duplicates for a document

		Args:
		        doc: Frappe document to check

		Returns:
		        List of dicts with {name, score, fields}
		"""
		# Get candidates using blocking strategy
		candidates = self._get_candidates(doc)

		if not candidates:
			return []

		# Score each candidate
		scored = []
		for candidate in candidates:
			score = self.calculate_similarity(doc, candidate)
			if score >= self.threshold:
				scored.append(
					{
						"name": candidate.name,
						"score": score,
						"fields": self._get_matching_fields(doc, candidate),
					}
				)

		# Sort by score descending
		scored.sort(key=lambda x: x["score"], reverse=True)

		return scored

	def _get_candidates(self, doc) -> list:
		"""
		Get candidate documents using blocking strategy
		Reduces search space from O(n) to O(m) where m << n

		Args:
		        doc: Document to find candidates for

		Returns:
		        List of candidate documents
		"""
		if not self.blocking_fields:
			# No blocking - search all documents (not recommended for large datasets)
			return frappe.get_all(doc.doctype, filters={"name": ["!=", doc.name]}, limit=1000)

		# Build blocking filter
		filters = {"name": ["!=", doc.name]}

		for field in self.blocking_fields:
			value = doc.get(field)
			if value:
				# Use first 3 characters for blocking (configurable)
				if isinstance(value, str) and len(value) >= 3:
					filters[field] = ["like", f"{value[:3]}%"]
				else:
					filters[field] = value

		# Get candidates that match blocking criteria
		candidates = frappe.get_all(doc.doctype, filters=filters, fields=["*"], limit=500)

		return [frappe.get_doc(doc.doctype, c.name) for c in candidates]

	def calculate_similarity(self, doc1, doc2) -> float:
		"""
		Calculate weighted similarity score between two documents

		Args:
		        doc1: First document
		        doc2: Second document

		Returns:
		        Similarity score (0-100)
		"""
		if not self.scoring_fields:
			# Default: compare all text fields
			return self._default_similarity(doc1, doc2)

		total_weight = sum(f.get("weight", 1.0) for f in self.scoring_fields)
		weighted_score = 0.0

		for field_config in self.scoring_fields:
			field = field_config.get("field")
			weight = field_config.get("weight", 1.0)
			scorer = field_config.get("scorer", "fuzzy")

			# Get field values
			val1 = doc1.get(field)
			val2 = doc2.get(field)

			if val1 is None or val2 is None:
				continue

			# Calculate field similarity
			field_score = self._score_field(val1, val2, scorer)
			weighted_score += field_score * (weight / total_weight)

		return weighted_score * 100  # Return 0-100 scale

	def _score_field(self, val1, val2, scorer: str) -> float:
		"""
		Score similarity between two field values

		Args:
		        val1: First value
		        val2: Second value
		        scorer: Scoring algorithm name

		Returns:
		        Similarity score (0.0-1.0)
		"""
		# Convert to strings
		str1 = str(val1).lower().strip()
		str2 = str(val2).lower().strip()

		if scorer == "exact":
			return 1.0 if str1 == str2 else 0.0

		elif scorer == "fuzzy":
			# Use Levenshtein ratio
			return fuzz.ratio(str1, str2) / 100.0

		elif scorer == "token":
			# Token sort ratio (good for names with different word orders)
			return fuzz.token_sort_ratio(str1, str2) / 100.0

		elif scorer == "partial":
			# Partial ratio (good for substring matches)
			return fuzz.partial_ratio(str1, str2) / 100.0

		elif scorer == "jaro":
			# Jaro-Winkler (good for short strings like names)
			from rapidfuzz.distance import JaroWinkler

			return JaroWinkler.normalized_similarity(str1, str2)

		else:
			# Default to fuzzy
			return fuzz.ratio(str1, str2) / 100.0

	def _get_matching_fields(self, doc1, doc2) -> dict:
		"""
		Get field-by-field comparison

		Args:
		        doc1: First document
		        doc2: Second document

		Returns:
		        Dict of field: similarity score
		"""
		fields = {}

		for field_config in self.scoring_fields:
			field = field_config.get("field")
			scorer = field_config.get("scorer", "fuzzy")

			val1 = doc1.get(field)
			val2 = doc2.get(field)

			if val1 is not None and val2 is not None:
				score = self._score_field(val1, val2, scorer)
				fields[field] = round(score * 100, 2)

		return fields

	def _default_similarity(self, doc1, doc2) -> float:
		"""
		Default similarity calculation when no scoring fields specified
		Uses all text fields from meta
		"""
		meta = frappe.get_meta(doc1.doctype)
		text_fields = [f.fieldname for f in meta.fields if f.fieldtype in ["Data", "Text", "Small Text"]]

		total_score = 0.0
		count = 0

		for field in text_fields:
			val1 = doc1.get(field)
			val2 = doc2.get(field)

			if val1 and val2:
				score = self._score_field(val1, val2, "fuzzy")
				total_score += score
				count += 1

		return (total_score / count) if count > 0 else 0.0

	@staticmethod
	def create_fingerprint(doc, fields: list[str]) -> str:
		"""
		Create a hash fingerprint for blocking/indexing

		Args:
		        doc: Document to fingerprint
		        fields: List of fields to include

		Returns:
		        Hash string
		"""
		import hashlib

		# Collect and normalize values
		values = []
		for field in fields:
			val = doc.get(field)
			if val:
				# Normalize: lowercase, strip, remove spaces
				normalized = str(val).lower().strip().replace(" ", "")
				values.append(normalized)

		# Create hash
		combined = "|".join(sorted(values))
		return hashlib.md5(combined.encode()).hexdigest()
