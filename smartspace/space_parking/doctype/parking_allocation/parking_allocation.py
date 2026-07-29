# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, now_datetime
from frappe.model.document import Document


class ParkingAllocation(Document):
	def before_save(self):
		if not self.allocation_date:
			self.allocation_date = today()
		if not self.allocated_from:
			self.allocated_from = now_datetime()

	def on_insert(self):
		frappe.db.set_value("Parking Slot", self.parking_slot, "status", "Occupied")


@frappe.whitelist()
def release_parking(name):
	doc = frappe.get_doc("Parking Allocation", name)
	if doc.allocation_status != "Active":
		frappe.throw("Only active allocations can be released")

	doc.allocation_status = "Completed"
	doc.allocated_to = now_datetime()
	doc.save(ignore_permissions=True)

	frappe.db.set_value("Parking Slot", doc.parking_slot, "status", "Available")
	return "Released"


@frappe.whitelist()
def find_vehicle(vehicle_number):
	results = frappe.get_all(
		"Parking Allocation",
		filters={"vehicle_number": ["like", f"%{vehicle_number}%"], "allocation_status": "Active"},
		fields=["name", "parking_slot", "vehicle_number", "member", "app_user", "allocated_from", "allocation_status"]
	)
	return results
