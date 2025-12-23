# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe


def execute():
    """
    Rename method_config to config in Rule Action table.
    This patch handles both the column rename and any JSON references.
    """
    # Check if old column exists
    if frappe.db.has_column("Rule Action", "method_config"):
        # Check if new column already exists (in case of partial migration)
        if not frappe.db.has_column("Rule Action", "config"):
            frappe.db.sql("""
                ALTER TABLE `tabRule Action`
                CHANGE COLUMN `method_config` `config` LONGTEXT
            """)
        else:
            # Both columns exist - copy data and drop old
            frappe.db.sql("""
                UPDATE `tabRule Action`
                SET `config` = `method_config`
                WHERE `config` IS NULL OR `config` = ''
            """)
            frappe.db.sql("""
                ALTER TABLE `tabRule Action`
                DROP COLUMN `method_config`
            """)
        
        frappe.db.commit()
