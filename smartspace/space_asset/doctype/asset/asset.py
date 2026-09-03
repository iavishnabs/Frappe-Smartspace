# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Asset(Document):
	def validate(self):
		if not self.serial_number and self.name:
			self.serial_number = f"SN-{self.name}"


@frappe.whitelist()
def get_asset_movements(asset):
	"""Get asset movement history from submitted asset allocations."""
	allocations = frappe.db.sql("""
		SELECT aa.name, aa.location, aa.allocated_from, aa.allocated_to
		FROM `tabAsset Allocation` aa
		INNER JOIN `tabAsset Allocation Item` aai ON aai.parent = aa.name
		WHERE aai.asset = %s AND aa.docstatus = 1
		ORDER BY aa.creation desc
	""", asset, as_dict=True)

	return allocations
