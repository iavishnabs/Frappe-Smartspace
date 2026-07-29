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


@frappe.whitelist()
def mark_returned(found_report, lost_report, returned_to):
	found_doc = frappe.get_doc("Lost And Found", found_report)
	if found_doc.status != "Open":
		frappe.throw("Only open reports can be marked as returned")

	found_doc.status = "Returned"
	found_doc.matched_report = lost_report
	found_doc.returned_to = returned_to
	found_doc.save(ignore_permissions=True)

	if lost_report:
		lost_doc = frappe.get_doc("Lost And Found", lost_report)
		if lost_doc.status == "Open":
			lost_doc.status = "Returned"
			lost_doc.matched_report = found_report
			lost_doc.returned_to = returned_to
			lost_doc.save(ignore_permissions=True)

	return "Returned"


@frappe.whitelist()
def close_report(name):
	doc = frappe.get_doc("Lost And Found", name)
	if doc.status != "Returned":
		frappe.throw("Only returned reports can be closed")

	doc.status = "Closed"
	doc.save(ignore_permissions=True)

	if doc.matched_report:
		matched = frappe.get_doc("Lost And Found", doc.matched_report)
		if matched.status != "Closed":
			matched.status = "Closed"
			matched.save(ignore_permissions=True)

	return "Closed"
