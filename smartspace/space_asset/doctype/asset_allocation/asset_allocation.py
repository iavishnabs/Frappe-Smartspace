# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssetAllocation(Document):
	def on_submit(self):
		for row in self.assets:
			self.update_asset_status(row.asset, "Allocated")

	def on_cancel(self):
		for row in self.assets:
			self.update_asset_status(row.asset, "Available")

	def before_save(self):
		if self.allocation_status == "Cancelled" and self.docstatus == 1:
			self.db_set("docstatus", 2)
			for row in self.assets:
				self.update_asset_status(row.asset, "Available")

	def update_asset_status(self, asset, status):
		if asset:
			frappe.db.set_value("Asset", asset, "status", status)
