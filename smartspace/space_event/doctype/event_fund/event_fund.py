# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventFund(Document):
	def before_save(self):
		self.update_totals()

	def update_totals(self):
		total_collection = frappe.db.sql("""
			SELECT COALESCE(SUM(amount), 0)
			FROM `tabMember Event Fund`
			WHERE event_fund = %s
		""", (self.name,))[0][0]

		total_expense = frappe.db.sql("""
			SELECT COALESCE(SUM(e.net_amount), 0)
			FROM `tabExpense` e
			WHERE e.event = %s AND e.status = 'Approved'
		""", (self.event,))[0][0]

		self.total_collection = total_collection
		self.total_expense = total_expense
		self.fund_balance = total_collection - total_expense


@frappe.whitelist()
def refresh_fund(fund_name):
	fund = frappe.get_doc("Event Fund", fund_name)
	fund.update_totals()
	fund.save(ignore_permissions=True)
	return "Refreshed"
