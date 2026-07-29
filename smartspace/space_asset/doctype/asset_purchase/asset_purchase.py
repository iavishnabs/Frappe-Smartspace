# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class AssetPurchase(Document):
	def on_submit(self):
		self.create_assets()
		self.calculate_total_cost()
		if frappe.db.get_single_value("App Settings", "auto_create_expense_on_asset_purchase"):
			expense_name = self.create_expense_entry()
			self.create_payment_entry(expense_name)
	
	def before_save(self):
		self.calculate_total_cost()

	def create_assets(self):
		total_created = 0
		for row in self.asset_purchase_items: 
			qty = int(row.qty or 0)
			if qty <= 0:
				continue

			for i in range(qty):
				asset_doc = frappe.get_doc({
					"doctype": "Asset",
					"asset_item": row.asset,
					"status": "Available",
					"enabled": 1,
					"unit_cost": row.price,
					"location": row.location,
					"description": row.description,
					"asset_purchase": self.name
				})
				asset_doc.insert(ignore_permissions=True)
				total_created += 1
		frappe.msgprint(f"{total_created} Asset(s) created from child table")
	def calculate_total_cost(self):
		for row in self.asset_purchase_items:
			row.total_price = (row.qty or 0) * (row.price or 0)
		self.net_amount = sum((row.total_price ) for row in self.asset_purchase_items)

	def create_expense_entry(self):
		expense_entry = frappe.new_doc("Expense")
		expense_entry.expense_date = self.purchase_date
		expense_entry.asset_purchase = self.name
		expense_entry.status = "Approved"

		for row in self.asset_purchase_items:
			expense_entry.append("expenses", {
				"expense_category": "Office Expense",
				"location": row.location,
				"amount": row.total_price,
				"description": row.description
			})
		expense_entry.insert(ignore_permissions=True)
		return expense_entry.name

	def create_payment_entry(self, expense_name):

		payment_entry = frappe.new_doc("Payment")
		payment_entry.payment_type = "Pay"
		payment_entry.user = frappe.session.user
		payment_entry.transaction_reference = "Expense"
		payment_entry.reference_name = expense_name
		payment_entry.reference_date = now_datetime()

		payment_entry.amount = self.net_amount
		payment_entry.payment_purpose = "Asset Purchase"
		payment_entry.payment_status = "Paid"
		payment_entry.insert(ignore_permissions=True)