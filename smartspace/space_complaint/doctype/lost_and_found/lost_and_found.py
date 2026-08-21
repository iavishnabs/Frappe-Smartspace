# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document


class LostAndFound(Document):
	def before_save(self):
		if not self.reported_date:
			self.reported_date = now_datetime()
		if not self.status:
			self.status = "Open"
