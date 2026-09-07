import frappe

from smartspace.frontend_api.auth import (
	get_session_user_location,
	get_session_app_user,
	get_session_app_user_doc,
	get_session_user_role,
	is_session_user_admin,
)
from smartspace.notification import create_notification_log


@frappe.whitelist()
def get_technicians(search=None, location=None, page=1, page_size=10):
	"""Get active technicians."""
	filters = {"staff_type": "Technician", "active": 1}

	is_admin = is_session_user_admin()
	user_location = get_session_user_location()

	if is_admin:
		if location and location != "All Locations":
			filters["location"] = location
	else:
		if user_location:
			filters["location"] = user_location

	if search:
		filters["full_name"] = ["like", f"%{search}%"]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	technicians = frappe.db.get_list(
		"Staff",
		filters=filters,
		fields=["name", "full_name", "email", "phone", "location", "active", "staff_type", "date_of_join", "date_of_birth"],
		order_by="full_name asc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Staff", filters=filters)

	locations = frappe.db.get_all("Location", fields=["name"], order_by="name asc")

	return {
		"technicians": technicians,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
		"locations": [loc.name for loc in locations],
		"is_admin": is_admin,
	}


@frappe.whitelist()
def get_asset_allocations(
	status=None, allocated_from=None, allocated_to=None, page=1, page_size=10
):
	"""Get asset allocations."""
	filters = {"docstatus": 1}

	user_location = get_session_user_location()
	if user_location:
		filters["location"] = user_location

	if status and status != "All Status":
		filters["allocation_status"] = status

	if allocated_from:
		filters["allocated_from"] = [">=", allocated_from]

	if allocated_to:
		filters["allocated_to"] = ["<=", allocated_to]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	allocations = frappe.db.get_list(
		"Asset Allocation",
		filters=filters,
		fields=[
			"name",
			"location",
			"floor",
			"space",
			"posting_date",
			"allocated_from",
			"allocated_to",
			"allocation_status",
		],
		order_by="posting_date desc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Asset Allocation", filters=filters)

	return {
		"allocations": allocations,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
	}


@frappe.whitelist()
def get_allocation_assets(allocation_name):
	"""Get allocation assets."""
	doc = frappe.get_doc("Asset Allocation", allocation_name)

	assets = []
	for row in doc.assets:
		asset = frappe.db.get_value(
			"Asset",
			row.asset,
			["name", "asset_item", "serial_number", "status", "location"],
			as_dict=True,
		)
		if asset:
			assets.append(asset)

	return {"assets": assets, "allocation_name": allocation_name}


@frappe.whitelist()
def get_spaces():
	"""Get spaces for the supervisor's location."""
	user_location = get_session_user_location()
	if not user_location:
		return {"spaces": [], "location": None}

	spaces = frappe.db.get_list(
		"Space",
		filters={"location": user_location},
		fields=[
			"name", "location", "floor", "space_type",
			"seating_capacity", "availability_status",
			"hourly_rate", "amenities", "description",
		],
		order_by="space_type asc, name asc",
	)

	return {"spaces": spaces, "location": user_location}


@frappe.whitelist()
def get_maintenance_tasks(
	status=None, search=None, date_from=None, date_to=None, page=1, page_size=10
):
	"""Get maintenance tasks."""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["name"] = ["like", f"%{search}%"]

	if date_from:
		filters["assigned_on"] = [">=", date_from]

	if date_to:
		if "assigned_on" in filters:
			filters["assigned_on"] = ["between", [date_from, date_to]]
		else:
			filters["assigned_on"] = ["<=", date_to]

	user_location = get_session_user_location()

	if user_location:
		technician_names = [s.name for s in frappe.get_all("Staff", filters={"location": user_location, "active": 1}, fields=["name"])]
		if technician_names:
			filters["technician"] = ["in", technician_names]
		else:
			filters["technician"] = "__nonexistent__"

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
def get_members(search=None, member_type=None, page=1, page_size=10):
	"""Get active members."""
	filters = {"active": 1}

	if member_type and member_type != "All Types":
		filters["member_type"] = member_type

	if search:
		filters["full_name"] = ["like", f"%{search}%"]

	user_location = get_session_user_location()

	if user_location:
		filters["location"] = user_location

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	members = frappe.db.get_list(
		"Member",
		filters=filters,
		fields=[
			"name",
			"full_name",
			"email",
			"phone",
			"member_type",
			"location",
			"join_date",
			"expiry_date",
			"gender",
			"active",
		],
		order_by="full_name asc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Member", filters=filters)

	return {
		"members": members,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
	}


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

	if scope == "mine":
		filters["raised_by"] = user_id
	elif scope == "others":
		filters["raised_by"] = ["!=", user_id]

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

		# lookup maintenance task for this complaint
		c["maintenance_task"] = None
		am_name = frappe.db.get_value("Asset Maintenance", {"complaint": c.name}, "name")
		if am_name:
			task = frappe.db.get_value(
				"Maintenance Task Allocation",
				{"asset_maintenance_request": am_name},
				["name", "status", "priority", "technician"],
				as_dict=True,
			)
			if task:
				task["technician_name"] = frappe.db.get_value("Staff", task.technician, "full_name") if task.technician else None
				c["maintenance_task"] = task

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
		else:
			pass

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

			# lookup phone and ID from Member/Staff
			item["reported_by_phone"] = None
			item["reported_by_id"] = None
			item["reported_by_id_type"] = None

			member = frappe.db.get_value("Member", {"app_user": item.reported_by}, ["name", "phone"])
			if member:
				item["reported_by_id"] = member[0]
				item["reported_by_phone"] = member[1]
				item["reported_by_id_type"] = "Member"
			else:
				staff = frappe.db.get_value("Staff", {"app_user": item.reported_by}, ["name", "phone"])
				if staff:
					item["reported_by_id"] = staff[0]
					item["reported_by_phone"] = staff[1]
					item["reported_by_id_type"] = "Staff"
		else:
			item["reported_by_name"] = None
			item["reported_by_phone"] = None
			item["reported_by_id"] = None
			item["reported_by_id_type"] = None

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
	is_admin = is_session_user_admin()

	doc = frappe.get_doc("Lost And Found", name)

	is_owner = doc.reported_by == app_user

	if status == "Closed" and not is_owner and not is_admin:
		frappe.throw("Only supervisors or admins can close others' reports")

	if not is_owner and not is_admin:
		frappe.throw("You can only edit your own reports")

	if not is_owner and status != "Closed":
		frappe.throw("You can only close others' reports")

	if is_owner and doc.status == "Closed" and status != "Closed":
		frappe.throw("Closed reports cannot be edited")

	if status == "Closed":
		doc.status = "Closed"

	if is_owner and doc.status == "Open":
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
	is_admin = is_session_user_admin()
	app_user = get_session_app_user()

	doc = frappe.get_doc("Lost And Found", name)

	is_owner = doc.reported_by == app_user

	if not is_owner and not is_admin:
		role = get_session_user_role()
		if role != "Supervisor":
			frappe.throw("You can only close your own reports")

	if doc.status != "Open":
		frappe.throw("Only open reports can be closed")

	doc.status = "Closed"
	doc.save(ignore_permissions=True)

	return {"success": True, "status": "Closed"}


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


@frappe.whitelist()
def get_dashboard_stats():
	"""Get supervisor dashboard stats."""
	from frappe.utils import now_datetime, add_days

	now = now_datetime()

	user_location = get_session_user_location()

	loc_filter = {"location": user_location} if user_location else {}
	loc_staff = []
	loc_asset_names = []
	loc_user_emails = []
	if user_location:
		loc_staff = [s.name for s in frappe.get_all("Staff", filters={"location": user_location, "active": 1}, fields=["name"])]
		loc_asset_names = [a.name for a in frappe.get_all("Asset", filters={"location": user_location}, fields=["name"])]
		loc_user_emails = [au.user for au in frappe.get_all("App User", filters={"location": user_location}, fields=["user"]) if au.user]

	# complaints
	complaint_statuses = ["Open", "Scheduled", "In Progress", "Flagged", "Resolved", "Closed"]
	complaint_counts = {}
	for s in complaint_statuses:
		base_filter = {"status": s}
		if user_location:
			asset_complaints = [c.name for c in frappe.get_all("Complaints", filters={"related_asset": ["in", loc_asset_names]}, fields=["name"])] if loc_asset_names else []
			user_complaints = [c.name for c in frappe.get_all("Complaints", filters={"raised_by": ["in", loc_user_emails], "related_asset": ["is", "not set"]}, fields=["name"])] if loc_user_emails else []
			valid = set(asset_complaints + user_complaints)
			if valid:
				base_filter["name"] = ["in", list(valid)]
			else:
				base_filter["name"] = "__nonexistent__"
		complaint_counts[s] = frappe.db.count("Complaints", base_filter)
	complaint_total = sum(complaint_counts.values())
	complaint_unsolved = complaint_counts["Open"] + complaint_counts["Scheduled"] + complaint_counts["In Progress"] + complaint_counts["Flagged"]
	complaint_solved = complaint_counts["Resolved"] + complaint_counts["Closed"]
	complaint_resolution_rate = round((complaint_solved / complaint_total * 100), 1) if complaint_total > 0 else 0

	# complaints in last 7 days for trend
	complaints_7d_filter = {"complaint_date": [">=", add_days(now, -7)]}
	if user_location:
		asset_complaints_7d = [c.name for c in frappe.get_all("Complaints", filters={"related_asset": ["in", loc_asset_names], "complaint_date": [">=", add_days(now, -7)]}, fields=["name"])] if loc_asset_names else []
		user_complaints_7d = [c.name for c in frappe.get_all("Complaints", filters={"raised_by": ["in", loc_user_emails], "related_asset": ["is", "not set"], "complaint_date": [">=", add_days(now, -7)]}, fields=["name"])] if loc_user_emails else []
		valid_7d = set(asset_complaints_7d + user_complaints_7d)
		if valid_7d:
			complaints_7d_filter["name"] = ["in", list(valid_7d)]
		else:
			complaints_7d_filter["name"] = "__nonexistent__"
	complaints_7d = frappe.db.count("Complaints", complaints_7d_filter)

	# maintenance tasks
	task_statuses = ["Open", "In Progress", "Flagged", "Overdue", "Completed"]
	task_counts = {}
	for s in task_statuses:
		base_filter = {"status": s}
		if user_location and loc_staff:
			base_filter["technician"] = ["in", loc_staff]
		elif user_location:
			base_filter["technician"] = "__nonexistent__"
		task_counts[s] = frappe.db.count("Maintenance Task Allocation", base_filter)
	task_total = sum(task_counts.values())
	task_completed = task_counts["Completed"]
	task_active = task_counts["Open"] + task_counts["In Progress"] + task_counts["Flagged"] + task_counts["Overdue"]
	task_completion_rate = round((task_completed / task_total * 100), 1) if task_total > 0 else 0

	# technician workload
	tech_filters = {"staff_type": "Technician", "active": 1}
	if user_location:
		tech_filters["location"] = user_location
	technicians = frappe.get_all(
		"Staff",
		filters=tech_filters,
		fields=["name", "full_name"],
	)
	tech_workload = []
	for tech in technicians:
		active_tasks = frappe.db.count(
			"Maintenance Task Allocation",
			{"technician": tech.name, "status": ["in", ["Open", "In Progress", "Flagged", "Overdue"]]},
		)
		completed_tasks = frappe.db.count(
			"Maintenance Task Allocation",
			{"technician": tech.name, "status": "Completed"},
		)
		tech_workload.append({
			"name": tech.name,
			"full_name": tech.full_name,
			"active_tasks": active_tasks,
			"completed_tasks": completed_tasks,
		})
	tech_workload.sort(key=lambda x: x["active_tasks"], reverse=True)

	# assets
	asset_statuses = ["Available", "Allocated", "Under Maintenance", "Damaged", "Decommissioned"]
	asset_counts = {}
	for s in asset_statuses:
		base_filter = {"status": s}
		if user_location:
			base_filter.update(loc_filter)
		asset_counts[s] = frappe.db.count("Asset", base_filter)
	asset_total = sum(asset_counts.values())
	asset_active = asset_counts["Available"] + asset_counts["Allocated"]
	asset_decommissioned = asset_counts["Decommissioned"]
	asset_damaged = asset_counts["Damaged"]
	asset_under_maintenance = asset_counts["Under Maintenance"]
	asset_health_rate = round(((asset_total - asset_decommissioned - asset_damaged) / asset_total * 100), 1) if asset_total > 0 else 0

	# members
	member_base = loc_filter.copy()
	member_total = frappe.db.count("Member", member_base)
	member_active = frappe.db.count("Member", {**member_base, "active": 1})
	member_inactive = member_total - member_active
	member_flex = frappe.db.count("Member", {**member_base, "active": 1, "member_type": "Flex"})
	member_regular = frappe.db.count("Member", {**member_base, "active": 1, "member_type": "Regular"})
	member_active_rate = round((member_active / member_total * 100), 1) if member_total > 0 else 0

	# new members in last 30 days
	new_members_30d = frappe.db.count("Member", {**member_base, "join_date": [">=", add_days(now, -30)]})

	# parking slots
	parking_base = {"enabled": 1}
	if user_location:
		parking_base.update(loc_filter)
	parking_statuses = ["Available", "Occupied", "Inactive"]
	parking_counts = {}
	for s in parking_statuses:
		parking_counts[s] = frappe.db.count("Parking Slot", {**parking_base, "status": s})
	parking_total = sum(parking_counts.values())
	parking_occupancy_rate = round((parking_counts["Occupied"] / parking_total * 100), 1) if parking_total > 0 else 0

	parking_types = ["Bike", "Car", "Visitor"]
	parking_by_type = {}
	for t in parking_types:
		parking_by_type[t] = {
			"total": frappe.db.count("Parking Slot", {**parking_base, "slot_type": t}),
			"available": frappe.db.count("Parking Slot", {**parking_base, "slot_type": t, "status": "Available"}),
			"occupied": frappe.db.count("Parking Slot", {**parking_base, "slot_type": t, "status": "Occupied"}),
		}

	# lost & found
	lf_base = loc_filter.copy()
	lf_open = frappe.db.count("Lost And Found", {**lf_base, "status": "Open"})
	lf_closed = frappe.db.count("Lost And Found", {**lf_base, "status": "Closed"})
	lf_total = lf_open + lf_closed

	# events
	event_base = {"event_status": "Published", "start_date": [">=", now]}
	if user_location:
		event_base.update(loc_filter)
	event_upcoming = frappe.db.count("Space Event", event_base)
	event_completed_filter = {"event_status": "Completed"}
	if user_location:
		event_completed_filter.update(loc_filter)
	event_completed = frappe.db.count("Space Event", event_completed_filter)
	event_draft_filter = {"event_status": "Draft"}
	if user_location:
		event_draft_filter.update(loc_filter)
	event_draft = frappe.db.count("Space Event", event_draft_filter)

	latest_event = frappe.db.get_list(
		"Space Event",
		filters=event_base,
		fields=["name", "event_name", "event_theme", "location", "start_date", "end_date", "description"],
		order_by="start_date asc",
		limit=1,
	)
	latest_event = latest_event[0] if latest_event else None

	# staff
	staff_base = {"active": 1}
	if user_location:
		staff_base.update(loc_filter)
	staff_total = frappe.db.count("Staff", staff_base)
	staff_technicians = frappe.db.count("Staff", {**staff_base, "staff_type": "Technician"})
	staff_supervisors = frappe.db.count("Staff", {**staff_base, "staff_type": "Supervisor"})
	staff_security = frappe.db.count("Staff", {**staff_base, "staff_type": "Security"})

	# recent complaints
	recent_comp_filter = {"status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]}
	if user_location:
		asset_comp_names = [c.name for c in frappe.get_all("Complaints", filters={"related_asset": ["in", loc_asset_names], "status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]}, fields=["name"])] if loc_asset_names else []
		user_comp_names = [c.name for c in frappe.get_all("Complaints", filters={"raised_by": ["in", loc_user_emails], "related_asset": ["is", "not set"], "status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]}, fields=["name"])] if loc_user_emails else []
		valid_comp = set(asset_comp_names + user_comp_names)
		if valid_comp:
			recent_comp_filter["name"] = ["in", list(valid_comp)]
		else:
			recent_comp_filter["name"] = "__nonexistent__"
	recent_complaints = frappe.db.get_list(
		"Complaints",
		filters=recent_comp_filter,
		fields=["name", "status", "complaint_date", "description", "assigned_to"],
		order_by="complaint_date desc",
		limit=5,
	)
	for c in recent_complaints:
		c["assigned_to_name"] = frappe.db.get_value("Staff", c.assigned_to, "full_name") if c.assigned_to else None

	# recent tasks
	recent_task_filter = {"status": ["in", ["Open", "In Progress", "Flagged", "Overdue"]]}
	if user_location and loc_staff:
		recent_task_filter["technician"] = ["in", loc_staff]
	elif user_location:
		recent_task_filter["technician"] = "__nonexistent__"
	recent_tasks = frappe.db.get_list(
		"Maintenance Task Allocation",
		filters=recent_task_filter,
		fields=["name", "status", "priority", "assigned_on", "technician"],
		order_by="assigned_on desc",
		limit=5,
	)
	for t in recent_tasks:
		t["technician_name"] = frappe.db.get_value("Staff", t.technician, "full_name") if t.technician else None

	return {
		"complaints": {
			"counts": complaint_counts,
			"total": complaint_total,
			"unsolved": complaint_unsolved,
			"solved": complaint_solved,
			"resolution_rate": complaint_resolution_rate,
			"last_7d": complaints_7d,
		},
		"tasks": {
			"counts": task_counts,
			"total": task_total,
			"completed": task_completed,
			"active": task_active,
			"completion_rate": task_completion_rate,
		},
		"technicians": {
			"total": staff_technicians,
			"workload": tech_workload[:5],
		},
		"assets": {
			"counts": asset_counts,
			"total": asset_total,
			"active": asset_active,
			"decommissioned": asset_decommissioned,
			"damaged": asset_damaged,
			"under_maintenance": asset_under_maintenance,
			"health_rate": asset_health_rate,
		},
		"members": {
			"total": member_total,
			"active": member_active,
			"inactive": member_inactive,
			"flex": member_flex,
			"regular": member_regular,
			"active_rate": member_active_rate,
			"new_30d": new_members_30d,
		},
		"parking": {
			"counts": parking_counts,
			"total": parking_total,
			"occupancy_rate": parking_occupancy_rate,
			"by_type": parking_by_type,
		},
		"lost_found": {
			"open": lf_open,
			"closed": lf_closed,
			"total": lf_total,
		},
		"events": {
			"upcoming": event_upcoming,
			"completed": event_completed,
			"draft": event_draft,
			"latest": latest_event,
		},
		"staff": {
			"total": staff_total,
			"technicians": staff_technicians,
			"supervisors": staff_supervisors,
			"security": staff_security,
		},
		"recent_complaints": recent_complaints,
		"recent_tasks": recent_tasks,
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
def approve_decommission(name, closed_reason=None):
	"""Approve decommission."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import approve_decommission as do_approve
	do_approve(name, closed_reason)
	return {"success": True, "message": "Asset decommissioned"}


@frappe.whitelist()
def reject_flag(name):
	"""Reject a flag."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import reject_flag as do_reject
	do_reject(name)
	return {"success": True, "message": "Flag rejected, task resumed"}


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


@frappe.whitelist()
def set_asset_damaged(name):
	"""Set asset to Damaged and cancel active allocations."""
	asset = frappe.db.get_value("Asset", name, ["name", "status", "enabled"], as_dict=True)
	if not asset:
		frappe.throw("Asset not found")

	if asset.status in ("Damaged", "Decommissioned"):
		frappe.throw(f"Asset is already {asset.status}")

	frappe.db.set_value("Asset", name, "status", "Damaged", update_modified=True)
	frappe.db.set_value("Asset", name, "enabled", 0, update_modified=True)

	cancelled_allocations = []
	allocation_names = frappe.db.get_all(
		"Asset Allocation Item",
		filters={"asset": name},
		pluck="parent",
	)

	active_allocations = frappe.db.get_all(
		"Asset Allocation",
		filters={
			"name": ["in", allocation_names] if allocation_names else [""],
			"allocation_status": "Active",
			"docstatus": 1,
		},
		pluck="name",
	)

	for alloc_name in active_allocations:
		alloc = frappe.get_doc("Asset Allocation", alloc_name)
		alloc.db_set("allocation_status", "Cancelled")
		alloc.db_set("docstatus", 2)
		cancelled_allocations.append(alloc_name)

	frappe.db.commit()

	return {
		"success": True,
		"message": f"Asset {name} set to Damaged",
		"cancelled_allocations": cancelled_allocations,
	}


@frappe.whitelist()
def get_notifications(page=1, page_size=20, unread_only=False):
	"""Get notifications."""
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
			"name", "subject", "for_user", "type", "email_content",
			"document_type", "document_name", "read", "attached_file",
			"from_user", "link", "creation",
		],
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
	"""Mark notification read."""
	frappe.db.set_value("Notification Log", name, "read", 1)
	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def mark_all_notifications_read():
	"""Mark all notifications read."""
	user = frappe.session.user
	frappe.db.set_value("Notification Log", {"for_user": user, "read": 0}, "read", 1)
	frappe.db.commit()
	return {"success": True}


# reservation management

@frappe.whitelist()
def get_reservations(status=None, search=None, page=1, page_size=20):
	"""Get reservations."""
	user_location = get_session_user_location()

	filters = {}
	if status and status != "All Status":
		filters["booking_status"] = status

	if user_location:
		space_names = [s.name for s in frappe.get_all("Space", {"location": user_location}, ["name"])]
		if space_names:
			filters["space"] = ["in", space_names]
		else:
			filters["space"] = "__NO_MATCH__"

	if search:
		search = search.strip()
		app_users = [au.name for au in frappe.get_all("App User", {"full_name": ["like", f"%{search}%"]}, ["name"])]
		if app_users:
			filters["app_user"] = ["in", app_users]
		else:
			filters["app_user"] = "__NO_MATCH__"

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	reservations = frappe.get_all(
		"Reservation",
		filters=filters,
		fields=["name", "app_user", "space", "booking_from", "booking_to",
				"booking_type", "booking_status", "payment_status", "total_amount",
				"booking_date", "count", "member_type", "payment"],
		order_by="booking_date desc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Reservation", filters)

	# pending count for badge
	pending_filters = dict(filters)
	pending_filters["booking_status"] = "Pending"
	pending_count = frappe.db.count("Reservation", pending_filters)

	# enrich with user and space info
	for r in reservations:
		if r.app_user:
			r.user_name = frappe.db.get_value("App User", r.app_user, "full_name") or r.app_user
			r.user_email = frappe.db.get_value("App User", r.app_user, "email") or ""
		if r.space:
			space_info = frappe.db.get_value("Space", r.space, ["space_type", "location", "seating_capacity"], as_dict=True)
			if space_info:
				r.space_type = space_info.space_type
				r.location = space_info.location
				r.seating_capacity = space_info.seating_capacity
		# check if member exists
		r.is_member = bool(frappe.db.exists("Member", {"app_user": r.app_user}))

	return {
		"reservations": reservations,
		"total": total,
		"pending_count": pending_count,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if page_size else 1,
	}


@frappe.whitelist()
def confirm_reservation(name):
	"""Confirm a reservation."""
	from smartspace.space_booking.doctype.reservation.reservation import confirm_reservation as _confirm

	reservation = frappe.db.get_value("Reservation", name, ["booking_status", "app_user"], as_dict=True)
	if not reservation:
		frappe.throw("Reservation not found")
	if reservation.booking_status != "Pending":
		frappe.throw("Only pending reservations can be confirmed")

	result = _confirm(name)

	# notify the user
	app_user_email = frappe.db.get_value("App User", reservation.app_user, "user")
	if app_user_email:
		create_notification_log(
			subject="Reservation Confirmed",
			for_user=app_user_email,
			document_type="Reservation",
			document_name=name,
		)

	return {"success": True, "message": result}


@frappe.whitelist()
def cancel_reservation(name, reason=None):
	"""Cancel a reservation."""
	reservation = frappe.db.get_value("Reservation", name, ["booking_status", "app_user"], as_dict=True)
	if not reservation:
		frappe.throw("Reservation not found")
	if reservation.booking_status in ["Completed", "Cancelled"]:
		frappe.throw(f"Cannot cancel a {reservation.booking_status} reservation")

	frappe.db.set_value("Reservation", name, "booking_status", "Cancelled", update_modified=True)

	# free up the space if it was occupied
	space = frappe.db.get_value("Reservation", name, "space")
	if space:
		frappe.db.set_value("Space", space, "availability_status", "Available")

	# notify the user
	app_user_email = frappe.db.get_value("App User", reservation.app_user, "user")
	if app_user_email:
		msg = f"Your reservation {name} has been cancelled."
		if reason:
			msg += f" Reason: {reason}"
		create_notification_log(
			subject="Reservation Cancelled",
			for_user=app_user_email,
			document_type="Reservation",
			document_name=name,
		)

	return {"success": True, "message": "Reservation cancelled"}