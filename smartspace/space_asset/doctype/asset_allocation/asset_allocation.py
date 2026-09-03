# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, getdate
from frappe.model.document import Document


class AssetAllocation(Document):
	def on_submit(self):
		for row in self.assets:
			self.update_asset_status(row.asset, "Allocated")
			if self.location and self.allocated_from and getdate(self.allocated_from) <= getdate(today()):
				asset_location = frappe.db.get_value("Asset", row.asset, "location")
				if asset_location != self.location:
					frappe.db.set_value("Asset", row.asset, "location", self.location)

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


def update_asset_locations():
	"""to update asset locations from allocations based on current date"""
	allocations = frappe.get_all(
		"Asset Allocation",
		filters={
			"docstatus": 1,
			"allocation_status": "Active",
			"allocated_from": ["<=" , today()],
		},
		fields=["name", "location"],
		order_by="creation desc",
	)

	updated_assets = set()
	for alloc in allocations:
		items = frappe.get_all(
			"Asset Allocation Item",
			filters={"parent": alloc.name},
			fields=["asset"],
		)
		for item in items:
			if item.asset in updated_assets:
				continue
			asset_location = frappe.db.get_value("Asset", item.asset, "location")
			if alloc.location and asset_location != alloc.location:
				frappe.db.set_value("Asset", item.asset, "location", alloc.location)
			updated_assets.add(item.asset)


def expire_asset_allocations():
	# Expire asset allocations based on allocated_to date
	expired = frappe.get_all(
		"Asset Allocation",
		filters={
			"allocation_status": "Active",
			"docstatus": 1,
			"allocated_to": ["<", today()],
		},
		pluck="name",
	)

	for name in expired:
		doc = frappe.get_doc("Asset Allocation", name)
		doc.allocation_status = "Expired"
		doc.db_set("allocation_status", "Expired")
		doc.db_set("docstatus", 2)
		for row in doc.assets:
			if row.asset:
				frappe.db.set_value("Asset", row.asset, "status", "Available")
