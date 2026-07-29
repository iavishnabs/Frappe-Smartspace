# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Expense(Document):
	def before_save(self):
		self.calculate_total_cost()

	def on_update(self):
		if self.event and self.status == "Approved":
			self.refresh_event_totals()

	def calculate_total_cost(self):
		self.net_amount = sum((row.amount ) for row in self.expenses)

	def refresh_event_totals(self):
		fund = frappe.db.get_value("Event Fund", {"event": self.event}, "name")
		if fund:
			fund_doc = frappe.get_doc("Event Fund", fund)
			fund_doc.update_totals()
			fund_doc.save(ignore_permissions=True)

		event = frappe.get_doc("Space Event", self.event)
		event.update_event_summary()
