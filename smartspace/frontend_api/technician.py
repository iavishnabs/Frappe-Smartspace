import frappe
from smartspace.frontend_api.auth import (
	get_session_app_user,
	get_session_app_user_doc,
	get_session_user_location,
	get_session_user_role,
	is_session_user_admin,
)
from smartspace.notification import create_notification_log


# profile


@frappe.whitelist()
def get_profile():
	"""Get user profile."""
	app_user = get_session_app_user_doc(
		["name", "first_name", "last_name", "full_name", "email", "location", "active"]
	)

	if not app_user:
		frappe.throw("No App User found for current session user")

	staff = frappe.db.get_value(
		"Staff",
		{"app_user": app_user.name},
		["name", "full_name", "phone", "staff_type", "email", "date_of_join", "date_of_birth", "location", "active"],
		as_dict=True,
	)

	profile = {
		"app_user": {
			"name": app_user.name,
			"first_name": app_user.first_name,
			"last_name": app_user.last_name,
			"full_name": app_user.full_name,
			"email": app_user.email,
			"location": app_user.location,
			"active": app_user.active,
		},
		"staff": None,
	}

	if staff:
		profile["staff"] = {
			"name": staff.name,
			"full_name": staff.full_name,
			"phone": staff.phone,
			"staff_type": staff.staff_type,
			"email": staff.email,
			"date_of_join": staff.date_of_join,
			"date_of_birth": staff.date_of_birth,
			"location": staff.location,
			"active": staff.active,
		}

	return profile


@frappe.whitelist()
def change_password(new_password, confirm_password):
	"""Change user password."""
	if not new_password or not confirm_password:
		frappe.throw("Both new password and confirm password are required")

	if new_password != confirm_password:
		frappe.throw("New password and confirm password do not match")

	if len(new_password) < 6:
		frappe.throw("Password must be at least 6 characters long")

	app_user_name = get_session_app_user()

	if not app_user_name:
		frappe.throw("No App User found for current session user")

	doc = frappe.get_doc("App User", app_user_name)

	current_password = doc.get_password("password")
	if current_password and current_password == new_password:
		frappe.throw("New password cannot be the same as your current password")

	doc.password = new_password
	doc.save(ignore_permissions=True)

	return {"success": True, "message": "Password changed successfully"}


# events


@frappe.whitelist()
def get_events(page=1, page_size=10):
	"""Get upcoming events."""
	from frappe.utils import now_datetime

	user_location = get_session_user_location()

	filters = {
		"event_status": "Published",
		"start_date": [">=", now_datetime()],
	}

	if user_location:
		filters["location"] = user_location

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	events = frappe.db.get_list(
		"Space Event",
		filters=filters,
		fields=[
			"name",
			"event_name",
			"location",
			"event_theme",
			"event_status",
			"start_date",
			"end_date",
			"description",
			"total_collected",
			"total_spent",
			"fund_balance",
		],
		order_by="start_date asc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Space Event", filters=filters)

	return {
		"events": events,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
	}


# lost & found


@frappe.whitelist()
def get_lost_found(
	report_type=None, status=None, search=None, scope="all", page=1, page_size=10
):
	"""Get lost and found."""
	filters = {}

	if report_type and report_type != "All Types":
		filters["report_type"] = report_type

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["item_name"] = ["like", f"%{search}%"]

	app_user = get_session_app_user()
	user_location = get_session_user_location()

	if user_location:
		filters["location"] = user_location

	if scope == "mine":
		if app_user:
			filters["reported_by"] = app_user
		else:
			filters["reported_by"] = "__nonexistent__"
	elif scope == "others":
		if app_user:
			filters["reported_by"] = ["!=", app_user]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	items = frappe.db.get_list(
		"Lost And Found",
		filters=filters,
		fields=[
			"name",
			"report_type",
			"reported_by",
			"item_name",
			"image",
			"location",
			"status",
			"reported_date",
			"description",
		],
		order_by="reported_date desc",
		start=start,
		limit=page_size,
	)

	for item in items:
		if item.reported_by:
			item["reported_by_name"] = frappe.db.get_value(
				"App User", item.reported_by, "full_name"
			) or item.reported_by
		else:
			item["reported_by_name"] = None

	total = frappe.db.count("Lost And Found", filters=filters)

	locations = frappe.db.get_all("Location", fields=["name"], order_by="name asc")

	user_role = get_session_user_role()
	is_admin = is_session_user_admin()

	return {
		"items": items,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
		"locations": [loc.name for loc in locations],
		"current_app_user": app_user,
		"current_user_role": user_role,
		"is_admin": is_admin,
	}


@frappe.whitelist()
def create_lost_found(
	report_type, item_name, description=None, image=None
):
	"""Create lost and found."""
	app_user = get_session_app_user()

	if not app_user:
		frappe.throw("No App User found for current session user")

	user_location = get_session_user_location()

	doc = frappe.get_doc({
		"doctype": "Lost And Found",
		"report_type": report_type,
		"reported_by": app_user,
		"item_name": item_name,
		"location": user_location,
		"description": description,
		"image": image,
	})
	doc.insert(ignore_permissions=True)

	return {
		"name": doc.name,
		"report_type": doc.report_type,
		"item_name": doc.item_name,
		"status": doc.status,
	}


@frappe.whitelist()
def update_lost_found(
	name, report_type=None, item_name=None, description=None, image=None, status=None
):
	"""Update lost and found."""
	app_user = get_session_app_user()

	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only edit your own reports")

	if doc.status == "Closed" and status != "Closed":
		frappe.throw("Closed reports cannot be edited")

	if status == "Closed":
		doc.status = "Closed"

	if doc.status == "Open":
		if report_type is not None:
			doc.report_type = report_type
		if item_name is not None:
			doc.item_name = item_name
		user_location = get_session_user_location()
		if user_location:
			doc.location = user_location
		if description is not None:
			doc.description = description
		if image is not None:
			doc.image = image if image else None

	doc.save(ignore_permissions=True)

	return {
		"name": doc.name,
		"report_type": doc.report_type,
		"item_name": doc.item_name,
		"status": doc.status,
	}


@frappe.whitelist()
def delete_lost_found(name):
	"""Delete lost and found."""
	app_user = get_session_app_user()

	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only delete your own reports")

	if doc.status != "Open":
		frappe.throw("Only open reports can be deleted")

	frappe.delete_doc("Lost And Found", name, ignore_permissions=True)

	return {"deleted": True, "name": name}


@frappe.whitelist()
def close_lost_found(name):
	"""Close lost and found."""
	app_user = get_session_app_user()

	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only close your own reports")

	if doc.status != "Open":
		frappe.throw("Only open reports can be closed")

	doc.status = "Closed"
	doc.save(ignore_permissions=True)

	return {"success": True, "status": "Closed"}


# complaints


@frappe.whitelist()
def get_complaints(status=None, search=None, complaint_type=None, scope="all", page=1, page_size=10):
	"""Get complaints."""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if complaint_type and complaint_type != "All Types":
		if complaint_type == "Non Asset":
			filters["complaint_type"] = ["in", ["General", "Facility Related"]]
		else:
			filters["complaint_type"] = complaint_type

	if search:
		filters["description"] = ["like", f"%{search}%"]

	user_location = get_session_user_location()
	user_id = frappe.session.user

	if user_location:
		filters["location"] = user_location

	filters["raised_by"] = user_id

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	complaints = frappe.db.get_list(
		"Complaints",
		filters=filters,
		fields=[
			"name",
			"complaint_type",
			"raised_by",
			"related_asset",
			"location",
			"status",
			"complaint_date",
			"description",
			"attachment",
			"assigned_to",
			"closed_date",
			"closed_reason",
		],
		order_by="complaint_date desc",
		start=start,
		limit=page_size,
	)

	for c in complaints:
		if c.assigned_to:
			c["assigned_to_name"] = frappe.db.get_value("Staff", c.assigned_to, "full_name")
		else:
			c["assigned_to_name"] = None

		if c.raised_by:
			c["raised_by_name"] = frappe.db.get_value("User", c.raised_by, "full_name") or c.raised_by
		else:
			c["raised_by_name"] = None

		if c.related_asset:
			asset = frappe.db.get_value(
				"Asset",
				c.related_asset,
				["name", "serial_number", "asset_item", "status", "location"],
				as_dict=True,
			)
			c["asset"] = asset
		else:
			c["asset"] = None

	total = frappe.db.count("Complaints", filters=filters)

	return {
		"complaints": complaints,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
		"current_user": frappe.session.user,
	}


@frappe.whitelist()
def create_complaint(complaint_type, description, related_asset=None, attachment=None):
	"""Create a complaint."""
	user_id = frappe.session.user

	doc = frappe.get_doc({
		"doctype": "Complaints",
		"complaint_type": complaint_type,
		"raised_by": user_id,
		"related_asset": related_asset if complaint_type == "Asset Related" else None,
		"location": get_session_user_location(),
		"description": description,
		"attachment": attachment,
		"status": "Open",
	})
	doc.insert(ignore_permissions=True)

	admin_users = frappe.get_all(
		"App User",
		filters={"active": 1, "role": "App Admin"},
		fields=["user"],
	)

	subject = f"New Complaint: {doc.name}"
	for admin in admin_users:
		if admin.user:
			create_notification_log(
				subject=subject,
				for_user=admin.user,
				document_type="Complaints",
				document_name=doc.name,
			)

	return {
		"name": doc.name,
		"complaint_type": doc.complaint_type,
		"status": doc.status,
	}


@frappe.whitelist()
def update_complaint(
	name, complaint_type=None, description=None, related_asset=None, attachment=None
):
	"""Update a complaint."""
	user_id = frappe.session.user

	doc = frappe.get_doc("Complaints", name)

	if doc.raised_by != user_id:
		frappe.throw("You can only edit your own complaints")

	if doc.status != "Open":
		frappe.throw("Only open complaints can be edited")

	if complaint_type is not None:
		doc.complaint_type = complaint_type
		if complaint_type == "Asset Related":
			doc.related_asset = related_asset
		else:
			doc.related_asset = None
	user_location = get_session_user_location()
	if user_location:
		doc.location = user_location
	if description is not None:
		doc.description = description
	if attachment is not None:
		doc.attachment = attachment if attachment else None

	doc.save(ignore_permissions=True)

	return {
		"name": doc.name,
		"complaint_type": doc.complaint_type,
		"status": doc.status,
	}


@frappe.whitelist()
def delete_complaint(name):
	"""Delete a complaint."""
	user_id = frappe.session.user

	doc = frappe.get_doc("Complaints", name)

	if doc.raised_by != user_id:
		frappe.throw("You can only delete your own complaints")

	if doc.status != "Open":
		frappe.throw("Only open complaints can be deleted")

	frappe.delete_doc("Complaints", name, ignore_permissions=True)

	return {"deleted": True, "name": name}


@frappe.whitelist()
def resolve_complaint(name):
	"""Resolve a complaint."""
	complaint = frappe.get_doc("Complaints", name)

	if complaint.complaint_type == "Asset Related":
		frappe.throw("Asset related complaints are resolved via technician assignment")

	if complaint.status == "Closed":
		frappe.throw("Closed complaints cannot be modified")

	complaint.status = "Resolved"
	complaint.save(ignore_permissions=True)

	return {"success": True, "status": "Resolved"}


# assets


@frappe.whitelist()
def get_assets(status=None, search=None, page=1, page_size=10):
	"""Get assets."""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["serial_number"] = ["like", f"%{search}%"]

	user_location = get_session_user_location()

	if user_location:
		filters["location"] = user_location

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	assets = frappe.db.get_list(
		"Asset",
		filters=filters,
		fields=[
			"name",
			"serial_number",
			"asset_item",
			"status",
			"location",
			"enabled",
			"unit_cost",
			"description",
		],
		order_by="modified desc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Asset", filters)

	for a in assets:
		if a.asset_item:
			a["asset_item_name"] = frappe.db.get_value("Asset Item", a.asset_item, "item_name") or a.asset_item
		else:
			a["asset_item_name"] = None
		if a.location:
			a["location_name"] = frappe.db.get_value("Location", a.location, "location_name") or a.location
		else:
			a["location_name"] = None

	total_pages = max(1, (total + page_size - 1) // page_size)

	return {
		"assets": assets,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": total_pages,
	}


# maintenance tasks


@frappe.whitelist()
def get_my_tasks(status=None, page=1, page_size=10):
	"""Get my tasks."""
	app_user = get_session_app_user()
	if not app_user:
		return {"tasks": [], "total": 0, "page": 1, "page_size": int(page_size), "total_pages": 1}

	staff_name = frappe.db.get_value("Staff", {"app_user": app_user}, "name")
	if not staff_name:
		return {"tasks": [], "total": 0, "page": 1, "page_size": int(page_size), "total_pages": 1}

	filters = {"technician": staff_name}

	if status and status != "All Status":
		filters["status"] = status

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	tasks = frappe.db.get_list(
		"Maintenance Task Allocation",
		filters=filters,
		fields=[
			"name",
			"asset_maintenance_request",
			"technician",
			"priority",
			"status",
			"assigned_on",
			"completed_on",
			"task_description",
		],
		order_by="assigned_on desc",
		start=start,
		limit=page_size,
	)

	for task in tasks:
		task["technician_name"] = frappe.db.get_value("Staff", task.technician, "full_name") if task.technician else None

		am = frappe.db.get_value(
			"Asset Maintenance",
			task.asset_maintenance_request,
			["asset", "reported_date", "maintenance_status", "issue_description"],
			as_dict=True,
		) if task.asset_maintenance_request else None

		if am and am.asset:
			asset = frappe.db.get_value(
				"Asset",
				am.asset,
				["name", "serial_number", "asset_item", "status", "location"],
				as_dict=True,
			)
			task["asset"] = asset
		else:
			task["asset"] = None

	total = frappe.db.count("Maintenance Task Allocation", filters=filters)

	return {
		"tasks": tasks,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
	}


@frappe.whitelist()
def start_task(name):
	"""Start a task."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import start_work
	start_work(name)
	return {"success": True, "message": "Work started"}


@frappe.whitelist()
def finish_task(name):
	"""Finish a task."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import finish_work
	finish_work(name)
	return {"success": True, "message": "Work completed"}


@frappe.whitelist()
def flag_task(name):
	"""Flag a task."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import flag_unusable
	flag_unusable(name)
	return {"success": True, "message": "Asset flagged as unusable, supervisor notified"}


@frappe.whitelist()
def get_dashboard_stats():
	"""Get technician dashboard stats."""
	from frappe.utils import now_datetime, add_days

	now = now_datetime()
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	staff_name = frappe.db.get_value("Staff", {"app_user": app_user}, "name")
	user_location = get_session_user_location()

	# my tasks
	task_statuses = ["Open", "In Progress", "Flagged", "Overdue", "Completed"]
	task_counts = {}
	for s in task_statuses:
		task_counts[s] = frappe.db.count("Maintenance Task Allocation", {"technician": staff_name, "status": s}) if staff_name else 0
	task_total = sum(task_counts.values())
	task_completed = task_counts["Completed"]
	task_active = task_counts["Open"] + task_counts["In Progress"] + task_counts["Flagged"] + task_counts["Overdue"]
	task_completion_rate = round((task_completed / task_total * 100), 1) if task_total > 0 else 0

	# recent active tasks
	recent_tasks = []
	if staff_name:
		recent_tasks = frappe.db.get_list(
			"Maintenance Task Allocation",
			filters={"technician": staff_name, "status": ["in", ["Open", "In Progress", "Flagged", "Overdue"]]},
			fields=["name", "status", "priority", "assigned_on", "task_description", "asset_maintenance_request"],
			order_by="assigned_on desc",
			limit=5,
		)
		for t in recent_tasks:
			am = frappe.db.get_value(
				"Asset Maintenance",
				t.asset_maintenance_request,
				["asset", "issue_description"],
				as_dict=True,
			) if t.asset_maintenance_request else None
			if am and am.asset:
				asset = frappe.db.get_value("Asset", am.asset, ["name", "serial_number", "asset_item", "status"], as_dict=True)
				t["asset"] = asset
			else:
				t["asset"] = None

	# my complaints
	complaint_statuses = ["Open", "Scheduled", "In Progress", "Flagged", "Resolved", "Closed"]
	complaint_counts = {}
	for s in complaint_statuses:
		complaint_counts[s] = frappe.db.count("Complaints", {"raised_by": frappe.session.user, "status": s})
	complaint_total = sum(complaint_counts.values())
	complaint_unsolved = complaint_counts["Open"] + complaint_counts["Scheduled"] + complaint_counts["In Progress"] + complaint_counts["Flagged"]
	complaint_solved = complaint_counts["Resolved"] + complaint_counts["Closed"]
	complaint_resolution_rate = round((complaint_solved / complaint_total * 100), 1) if complaint_total > 0 else 0

	recent_complaints = frappe.db.get_list(
		"Complaints",
		filters={"raised_by": frappe.session.user, "status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]},
		fields=["name", "status", "complaint_date", "description", "complaint_type"],
		order_by="complaint_date desc",
		limit=5,
	)

	# events
	event_base = {"event_status": "Published", "start_date": [">=", now]}
	if user_location:
		event_base.update({"location": user_location})
	event_upcoming = frappe.db.count("Space Event", event_base)

	latest_event = frappe.db.get_list(
		"Space Event",
		filters=event_base,
		fields=["name", "event_name", "event_theme", "location", "start_date", "end_date", "description"],
		order_by="start_date asc",
		limit=1,
	)
	latest_event = latest_event[0] if latest_event else None

	return {
		"tasks": {
			"counts": task_counts,
			"total": task_total,
			"completed": task_completed,
			"active": task_active,
			"completion_rate": task_completion_rate,
		},
		"complaints": {
			"counts": complaint_counts,
			"total": complaint_total,
			"unsolved": complaint_unsolved,
			"solved": complaint_solved,
			"resolution_rate": complaint_resolution_rate,
		},
		"recent_tasks": recent_tasks,
		"recent_complaints": recent_complaints,
		"events": {
			"upcoming": event_upcoming,
			"latest": latest_event,
		},
	}


# notifications


@frappe.whitelist()
def get_notifications(page=1, page_size=20, unread_only=False):
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
		fields=["name", "subject", "for_user", "type", "email_content",
				"document_type", "document_name", "read", "attached_file",
				"from_user", "link", "creation"],
		order_by="creation desc",
		start=start,
		limit=page_size,
	)
	total = frappe.db.count("Notification Log", filters=filters)
	unread_count = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
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
	frappe.db.set_value("Notification Log", name, "read", 1)
	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def mark_all_notifications_read():
	user = frappe.session.user
	frappe.db.set_value("Notification Log", {"for_user": user, "read": 0}, "read", 1)
	frappe.db.commit()
	return {"success": True}
