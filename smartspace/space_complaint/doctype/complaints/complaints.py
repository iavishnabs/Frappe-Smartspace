# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today
from frappe.model.document import Document
from smartspace.notification import notify_supervisor_on_new_complaint

class Complaints(Document):
	def after_insert(self):
		notify_supervisor_on_new_complaint(self)


@frappe.whitelist()
def assign_technician(
    complaint,
    reported_date,
    priority,
    task_description
):
    complaint_doc = frappe.get_doc("Complaints", complaint)

    # Find least busy technician for asset location
    technician = get_least_busy_technician(complaint_doc)

    if not technician:
        return {
            "success": False,
            "message": "No active technician available for this asset location."
        }

    # Update Complaint
    complaint_doc.assigned_to = technician
    complaint_doc.status = "Scheduled"
    complaint_doc.save(ignore_permissions=True)

    # Set asset to Under Maintenance
    frappe.db.set_value("Asset", complaint_doc.related_asset, "status", "Under Maintenance")

    # Create Asset Maintenance
    maintenance = frappe.get_doc({
        "doctype": "Asset Maintenance",
        "asset": complaint_doc.related_asset,
        "complaint": complaint_doc.name,
        "reported_date": reported_date,
        "maintenance_status": "Scheduled",
        "issue_description": complaint_doc.description
    })

    maintenance.insert(ignore_permissions=True)

    # Create Maintenance Task Allocation
    request = frappe.get_doc({
        "doctype": "Maintenance Task Allocation",
        "asset_maintenance_request": maintenance.name,
        "technician": technician,
        "priority": priority,
        "status": "Open",
        "assigned_on": today(),
        "task_description": task_description
    })

    request.insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "technician": technician,
        "maintenance": maintenance.name,
        "request": request.name
    }


def get_least_busy_technician(complaint_doc):
    asset_location = frappe.db.get_value(
        "Asset",
        complaint_doc.related_asset,
        "location"
    )

    technicians = frappe.get_all(
        "Staff",
        filters={
            "staff_type": "Technician",
            "active": 1,
            "location": asset_location
        },
        fields=["name"]
    )

    if not technicians:
        frappe.log_error(
            title="Technician Assignment Failed",
            message=(
                f"Complaint: {complaint_doc.name}\n"
                f"Asset: {complaint_doc.related_asset}\n"
                f"Location: {asset_location}\n"
                f"No active technician found."
            )
        )
        return None

    selected = None
    min_count = None

    for tech in technicians:
        count = frappe.db.count(
            "Maintenance Task Allocation",
            {
                "technician": tech.name,
                "status": ["in", ["Open", "In Progress", "Flagged", "Overdue"]]
            }
        )

        if min_count is None or count < min_count:
            min_count = count
            selected = tech.name

    return selected