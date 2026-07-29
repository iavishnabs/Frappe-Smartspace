# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe.model.document import Document


class MemberEventFund(Document):
	def before_save(self):
		if not self.payment_on:
			self.payment_on = today()

	def on_insert(self):
		self.create_payment()
		self.refresh_event_fund()

	def create_payment(self):
		if self.payment:
			return

		app_user = frappe.db.get_value("Member", self.member, "app_user")

		payment = frappe.get_doc({
			"doctype": "Payment",
			"payment_type": "Receive",
			"user": app_user,
			"amount": self.amount,
			"payment_status": "Paid",
			"payment_purpose": f"Event Fund - {self.event}",
			"transaction_reference": "Member Event Fund",
			"reference_name": self.name,
			"payment_date": frappe.utils.now_datetime()
		})
		payment.insert(ignore_permissions=True)
		self.payment = payment.name
		frappe.db.set_value("Member Event Fund", self.name, "payment", payment.name)

	def refresh_event_fund(self):
		if not self.event_fund:
			return
		fund = frappe.get_doc("Event Fund", self.event_fund)
		fund.update_totals()
		fund.save(ignore_permissions=True)
