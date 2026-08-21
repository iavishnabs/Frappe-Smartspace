# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe.model.document import Document


class MaintenanceTaskAllocation(Document):
	pass


@frappe.whitelist()
def start_work(name):
	doc = frappe.get_doc("Maintenance Task Allocation", name)
	doc.status = "In Progress"
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def finish_work(name):
	doc = frappe.get_doc("Maintenance Task Allocation", name)
	doc.status = "Completed"
	doc.completed_on = today()
	doc.save(ignore_permissions=True)

	maintenance = frappe.get_doc("Asset Maintenance", doc.asset_maintenance_request)
	maintenance.maintenance_status = "Completed"
	maintenance.save(ignore_permissions=True)

	frappe.db.set_value("Asset", maintenance.asset, "status", "Allocated")

	if maintenance.complaint:
		complaint = frappe.get_doc("Complaints", maintenance.complaint)
		complaint.status = "Resolved"
		complaint.save(ignore_permissions=True)

	notify_supervisor(doc, maintenance, "Completed")
	return True


@frappe.whitelist()
def flag_unusable(name):
	doc = frappe.get_doc("Maintenance Task Allocation", name)
	doc.status = "Flagged"
	doc.save(ignore_permissions=True)

	maintenance = frappe.get_doc("Asset Maintenance", doc.asset_maintenance_request)
	maintenance.maintenance_status = "Flagged"
	maintenance.save(ignore_permissions=True)

	if maintenance.complaint:
		complaint = frappe.get_doc("Complaints", maintenance.complaint)
		complaint.status = "Flagged"
		complaint.save(ignore_permissions=True)

	notify_supervisor(doc, maintenance, "Flagged as Unusable")
	return True


@frappe.whitelist()
def approve_decommission(name, closed_reason=None):
	doc = frappe.get_doc("Maintenance Task Allocation", name)
	doc.status = "Completed"
	doc.completed_on = today()
	doc.save(ignore_permissions=True)

	maintenance = frappe.get_doc("Asset Maintenance", doc.asset_maintenance_request)
	maintenance.maintenance_status = "Completed"
	maintenance.save(ignore_permissions=True)

	asset = frappe.get_doc("Asset", maintenance.asset)
	asset.status = "Decommissioned"
	asset.enabled = 0
	asset.save(ignore_permissions=True)

	frappe.db.set_value("Asset Allocation",
		{"name": ["in", frappe.db.get_all("Asset Allocation Item",
			{"asset": maintenance.asset}, "parent", pluck="parent")],
		 "allocation_status": "Active"},
		"allocation_status", "Cancelled"
	)

	if maintenance.complaint:
		complaint = frappe.get_doc("Complaints", maintenance.complaint)
		complaint.status = "Closed"
		complaint.closed_date = today()
		complaint.closed_reason = closed_reason
		complaint.save(ignore_permissions=True)

	notify_technician(doc, "Decommission Approved")
	frappe.db.commit()
	return True


@frappe.whitelist()
def reject_flag(name):
	doc = frappe.get_doc("Maintenance Task Allocation", name)
	doc.status = "In Progress"
	doc.save(ignore_permissions=True)

	maintenance = frappe.get_doc("Asset Maintenance", doc.asset_maintenance_request)
	maintenance.maintenance_status = "In Progress"
	maintenance.save(ignore_permissions=True)

	if maintenance.complaint:
		complaint = frappe.get_doc("Complaints", maintenance.complaint)
		complaint.status = "In Progress"
		complaint.save(ignore_permissions=True)

	notify_technician(doc, "Flag Rejected - Resume Work")
	return True


def notify_supervisor(mta_doc, maintenance, action):
	asset_location = frappe.db.get_value("Asset", maintenance.asset, "location")
	if not asset_location:
		return

	supervisors = frappe.get_all(
		"Staff",
		filters={"staff_type": "Supervisor", "active": 1, "location": asset_location},
		fields=["app_user"]
	)

	subject = f"Task {mta_doc.name} {action} by Technician"

	for supervisor in supervisors:
		if not supervisor.app_user:
			continue
		user = frappe.db.get_value("App User", supervisor.app_user, "user")
		if not user:
			continue
		from smartspace.notification import create_notification_log
		create_notification_log(
			subject=subject,
			for_user=user,
			document_type="Maintenance Task Allocation",
			document_name=mta_doc.name,
		)


def notify_technician(mta_doc, action):
	if not mta_doc.technician:
		return
	user = frappe.db.get_value("Staff", mta_doc.technician, "app_user")
	if not user:
		return
	user = frappe.db.get_value("App User", user, "user")
	if not user:
		return
	subject = f"Task {mta_doc.name} - {action}"
	from smartspace.notification import create_notification_log
	create_notification_log(
		subject=subject,
		for_user=user,
		document_type="Maintenance Task Allocation",
		document_name=mta_doc.name,
	)
