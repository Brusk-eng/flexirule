# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Rule Scheduler - Schedule rule execution on document batches.

Mirrors Frappe's Scheduled Job Type pattern:
- croniter for cron parsing
- is_event_due() for timing checks
- rq_job_id for deduplication
"""

import json
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime
from frappe.utils.background_jobs import is_job_enqueued


class RuleScheduler(Document):
    def validate(self):
        self._validate_cron_format()
        self._validate_rule()

    def _validate_cron_format(self):
        """Validate cron expression if frequency is Cron."""
        if self.frequency == "Cron" and self.cron_format:
            try:
                from croniter import croniter

                croniter(self.cron_format)
            except Exception:
                frappe.throw(
                    _("{0} is not a valid Cron expression").format(self.cron_format)
                )

    def _validate_rule(self):
        """Ensure linked rule exists and is active."""
        if self.rule:
            rule_doc = frappe.get_cached_doc("Rule", self.rule)
            if not rule_doc.is_active:
                frappe.msgprint(
                    _("Warning: Rule {0} is not active").format(self.rule),
                    indicator="orange",
                )

    @property
    def next_execution(self):
        """Virtual field - computed next execution time."""
        return self.get_next_execution()

    def get_next_execution(self):
        """
        Calculate next execution time based on frequency.
        Mirrors Frappe Scheduled Job Type pattern.
        """
        from croniter import croniter

        CRON_MAP = {
            "All": "*/5 * * * *",  # Every 5 minutes
            "Hourly": "0 * * * *",
            "Daily": "0 0 * * *",
            "Weekly": "0 0 * * 0",
            "Monthly": "0 0 1 * *",
        }

        cron = self.cron_format or CRON_MAP.get(self.frequency, "0 * * * *")
        last = get_datetime(self.last_execution or self.creation)
        return croniter(cron, last).get_next(datetime)

    def is_event_due(self, current_time=None):
        """Check if scheduler should run."""
        return self.get_next_execution() <= (current_time or now_datetime())

    @property
    def rq_job_id(self):
        """Unique ID for job deduplication."""
        return f"rule_scheduler::{self.name}"

    def enqueue(self, force=False):
        """
        Enqueue scheduler for execution if due.
        Returns True if enqueued.
        """
        if self.stopped:
            return False

        if self.is_event_due() or force:
            if not is_job_enqueued(self.rq_job_id):
                frappe.enqueue(
                    "flexirule.ruleflow.scheduler.run_scheduled_rule",
                    scheduler_name=self.name,
                    queue=self.get_queue_name(),
                    job_id=self.rq_job_id,
                    timeout=3600,  # 1 hour max
                )
                return True
            else:
                frappe.logger("flexirule").debug(
                    f"Skipped {self.name}: already in queue"
                )
        return False

    def get_queue_name(self):
        """Determine queue based on frequency."""
        if self.frequency in ("Daily", "Weekly", "Monthly"):
            return "long"
        return "default"

    def execute(self):
        """
        Execute the scheduled rule batch.
        Called from background job.
        """
        from flexirule.ruleflow.core.coordinator import RuleCoordinator

        batch_id = (
            f"BATCH-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}-{self.name}"
        )

        try:
            rule_doc = frappe.get_cached_doc("Rule", self.rule)
            if not rule_doc.is_active:
                frappe.log_error(
                    f"Scheduler {self.name}: Rule {self.rule} is not active"
                )
                return

            # Get documents to process
            documents = self._get_documents()

            if not documents:
                frappe.logger("flexirule").info(
                    f"Scheduler {self.name}: No documents to process"
                )
                self._update_last_execution()
                return

            success_count = 0
            error_count = 0

            for i, doc_name in enumerate(documents):
                try:
                    doc = frappe.get_doc(
                        self.filter_doctype or rule_doc.document_type, doc_name
                    )

                    context = {
                        "doc": doc,
                        "batch_id": batch_id,
                        "batch_index": i + 1,
                        "batch_total": len(documents),
                        "scheduler": self.name,
                    }

                    RuleCoordinator.execute_rule(rule_doc, context)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    frappe.log_error(
                        f"Scheduler {self.name}: Failed on {doc_name}", str(e)
                    )
                    if self.on_error == "Stop":
                        break

                # Commit every batch_size documents
                if (i + 1) % (self.batch_size or 100) == 0:
                    frappe.db.commit()
                    frappe.publish_realtime(
                        "batch_progress",
                        {
                            "batch_id": batch_id,
                            "processed": i + 1,
                            "total": len(documents),
                            "success": success_count,
                            "errors": error_count,
                        },
                    )

            frappe.db.commit()
            self._update_last_execution()

            frappe.logger("flexirule").info(
                f"Scheduler {self.name}: Completed. Success: {success_count}, Errors: {error_count}"
            )

        except Exception as e:
            frappe.log_error(f"Scheduler {self.name} failed", str(e))

    def _get_documents(self):
        """Get documents matching filter criteria."""
        doctype = self.filter_doctype
        if not doctype:
            # Fall back to rule's document_type
            rule_doc = frappe.get_cached_doc("Rule", self.rule)
            doctype = rule_doc.document_type

        filters = {}
        if self.filter_json:
            try:
                filters = json.loads(self.filter_json)
            except json.JSONDecodeError:
                frappe.log_error(f"Invalid filter JSON in {self.name}")

        return frappe.get_all(
            doctype,
            filters=filters,
            pluck="name",
            limit=1000,  # Safety limit
        )

    def _update_last_execution(self):
        """Update last_execution timestamp."""
        self.db_set("last_execution", now_datetime(), update_modified=False)


@frappe.whitelist()
def execute_now(doc: str):
    """Server action: Execute scheduler immediately."""
    frappe.only_for("System Manager")
    doc = json.loads(doc)
    scheduler = frappe.get_doc("Rule Scheduler", doc.get("name"))
    scheduler.enqueue(force=True)
    frappe.msgprint(_("Scheduler enqueued for execution"))
    return doc
