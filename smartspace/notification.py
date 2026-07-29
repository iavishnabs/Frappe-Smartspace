import frappe


def notify_supervisor_on_new_complaint(complaint):
    location = None
    
    # Asset Related Complaint
    if complaint.related_asset:

        location = frappe.db.get_value(
            "Asset",
            complaint.related_asset,
            "location"
        )

    # Faculty / General Complaint
    elif complaint.raised_by:

        location = frappe.db.get_value(
            "App User",
            {"user": complaint.raised_by},
            "location"
        )

    if not location:
        frappe.log_error(
            title="Complaint Notification Failed",
            message=(
                f"Complaint: {complaint.name}\n"
                f"Raised By: {complaint.raised_by}\n"
                f"Related Asset: {complaint.related_asset}\n"
                f"Unable to determine location."
            )
        )
        return

    supervisors = frappe.get_all(
        "Staff",
        filters={
            "staff_type": "Supervisor",
            "active": 1,
            "location": location
        },
        fields=["app_user"]
    )

    if not supervisors:
        frappe.log_error(
            title="Complaint Notification Failed",
            message=(
                f"Complaint: {complaint.name}\n"
                f"Location: {location}\n"
                f"No active supervisors found."
            )
        )
        return

    for supervisor in supervisors:

        if not supervisor.app_user:
            continue

        user = frappe.db.get_value("App User", supervisor.app_user, "user")

        if not user:
            continue

        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"New Complaint: {complaint.name}",
                "for_user": user,
                "type": "Alert",
                "document_type": complaint.doctype,
                "document_name": complaint.name
            }).insert(ignore_permissions=True)

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed notifying supervisor {user}"
            )