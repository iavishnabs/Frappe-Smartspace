# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Asset(Document):
	def validate(self):
		if not self.serial_number and self.name:
			self.serial_number = f"SN-{self.name}"
			
