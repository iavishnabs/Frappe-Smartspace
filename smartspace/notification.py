import frappe


def create_notification_log(subject, for_user, document_type=None, document_name=None):
    """Create notification log."""
    if not for_user:
        return
    if not frappe.db.get_single_value("App Settings", "enable_notifications"):
        return

    existing = frappe.db.exists(
        "Notification Log",
        {
            "subject": subject,
            "for_user": for_user,
            "document_type": document_type,
            "document_name": document_name,
        },
    )
    if existing:
        return

    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": subject,
            "for_user": for_user,
            "type": "Alert",
            "document_type": document_type,
            "document_name": document_name,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed creating Notification Log for {for_user}: {subject}",
        )


def on_lost_found_insert(doc, method=None):
    """Notify users about lost found."""
    owner_user = frappe.db.get_value("App User", doc.reported_by, "user") if doc.reported_by else None

    # figure out the report location
    report_location = doc.location
    if not report_location and doc.reported_by:
        report_location = frappe.db.get_value("App User", doc.reported_by, "location")

    if not report_location:
        return

    notified_users = set()
    subject = f"New {doc.report_type} Report: {doc.item_name}"

    # notify app users whose profile location matches
    active_users = frappe.get_all(
        "App User",
        filters={"active": 1, "location": report_location},
        fields=["user"],
    )
    for au in active_users:
        if not au.user or au.user == owner_user or au.user in notified_users:
            continue
        create_notification_log(
            subject=subject,
            for_user=au.user,
            document_type="Lost And Found",
            document_name=doc.name,
        )
        notified_users.add(au.user)

    # notify members with bookings at this location
    members_with_bookings = frappe.db.sql("""
        SELECT DISTINCT au.user
        FROM `tabReservation` r
        JOIN `tabSpace` s ON r.space = s.name
        JOIN `tabApp User` au ON r.app_user = au.name
        WHERE s.location = %s
        AND r.booking_status = 'Booked'
        AND au.user IS NOT NULL
    """, (report_location,), as_dict=True)
    for row in members_with_bookings:
        if not row.user or row.user == owner_user or row.user in notified_users:
            continue
        create_notification_log(
            subject=subject,
            for_user=row.user,
            document_type="Lost And Found",
            document_name=doc.name,
        )
        notified_users.add(row.user)

    # notify staff at this location
    staff = frappe.get_all("Staff", filters={"active": 1, "location": report_location}, fields=["app_user"])
    for s in staff:
        if not s.app_user:
            continue
        user = frappe.db.get_value("App User", s.app_user, "user")
        if not user or user == owner_user or user in notified_users:
            continue
        create_notification_log(
            subject=subject,
            for_user=user,
            document_type="Lost And Found",
            document_name=doc.name,
        )
        notified_users.add(user)


def notify_supervisor_on_new_complaint(complaint):
    location = None
    
    # asset related complaint
    if complaint.related_asset:

        location = frappe.db.get_value(
            "Asset",
            complaint.related_asset,
            "location"
        )

    # faculty / general complaint
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

        create_notification_log(
            subject=f"New Complaint: {complaint.name}",
            for_user=user,
            document_type=complaint.doctype,
            document_name=complaint.name,
        )


def on_notification_log_insert(doc, method=None):
    """Publish realtime notification."""
    if not doc.for_user:
        return

    frappe.publish_realtime(
        "smartspace_notification",
        {
            "name": doc.name,
            "subject": doc.subject,
            "for_user": doc.for_user,
            "type": doc.type,
            "document_type": doc.document_type,
            "document_name": doc.document_name,
            "read": doc.read,
            "creation": str(doc.creation) if doc.creation else None,
        },
        user=doc.for_user,
        after_commit=True,
    )


@frappe.whitelist()
def get_notifications(page=1, page_size=20, unread_only=False):
    """Get user notifications."""
    user = frappe.session.user
    filters = {"for_user": user}

    if unread_only and unread_only != "false":
        filters["read"] = 0

    page = int(page)
    page_size = int(page_size)
    start = (page - 1) * page_size

    notifications = frappe.db.get_list(
        "Notification Log",
        filters=filters,
        fields=[
            "name",
            "subject",
            "for_user",
            "type",
            "email_content",
            "document_type",
            "document_name",
            "read",
            "attached_file",
            "from_user",
            "link",
            "creation",
        ],
        order_by="creation desc",
        start=start,
        limit=page_size,
    )

    total = frappe.db.count("Notification Log", filters=filters)
    unread_count = frappe.db.count(
        "Notification Log",
        {"for_user": user, "read": 0},
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@frappe.whitelist()
def mark_notification_read(name):
    """Mark notification read."""
    frappe.db.set_value("Notification Log", name, "read", 1)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def mark_all_notifications_read():
    """Mark all notifications read."""
    user = frappe.session.user
    frappe.db.set_value(
        "Notification Log",
        {"for_user": user, "read": 0},
        "read",
        1,
    )
    frappe.db.commit()
    return {"success": True}