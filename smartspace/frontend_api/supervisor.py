import frappe


@frappe.whitelist()
def get_technicians(search=None, location=None, page=1, page_size=10):
	"""Return active technicians with filtering and pagination.

	Filters:
	- search: text search on full_name or email
	- location: Location name
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {"staff_type": "Technician", "active": 1}

	if location and location != "All Locations":
		filters["location"] = location

	if search:
		filters["full_name"] = ["like", f"%{search}%"]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	technicians = frappe.db.get_list(
		"Staff",
		filters=filters,
		fields=["name", "full_name", "email", "phone", "location", "active", "staff_type"],
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
	}


@frappe.whitelist()
def get_asset_allocations(
	location=None, allocated_from=None, allocated_to=None, page=1, page_size=10
):
	"""Return submitted asset allocations with filtering and pagination.

	Filters:
	- location: Location name
	- allocated_from: date range start (allocated_from >= this)
	- allocated_to: date range end (allocated_to <= this)
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {"docstatus": 1}

	if location and location != "All Locations":
		filters["location"] = location

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

	locations = frappe.db.get_all("Location", fields=["name"], order_by="name asc")

	return {
		"allocations": allocations,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
		"locations": [loc.name for loc in locations],
	}


@frappe.whitelist()
def get_allocation_assets(allocation_name):
	"""Return assets linked to a specific asset allocation.

	Returns list of {asset_id, asset_item, serial_number, status, location}.
	"""
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
def get_maintenance_tasks(
	status=None, date_from=None, date_to=None, page=1, page_size=10
):
	"""Return maintenance task allocations with filtering and pagination.

	Filters:
	- status: task status (Open, In Progress, Flagged, Overdue, Completed)
	- date_from: assigned_on >= this date
	- date_to: assigned_on <= this date
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if date_from:
		filters["assigned_on"] = [">=", date_from]

	if date_to:
		if "assigned_on" in filters:
			filters["assigned_on"] = ["between", [date_from, date_to]]
		else:
			filters["assigned_on"] = ["<=", date_to]

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
	"""Return active members with filtering and pagination.

	Filters:
	- search: text search on full_name, email, or phone
	- member_type: Flex or Regular
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {"active": 1}

	if member_type and member_type != "All Types":
		filters["member_type"] = member_type

	if search:
		filters["full_name"] = ["like", f"%{search}%"]

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
def get_complaints(status=None, search=None, page=1, page_size=10):
	"""Return complaints with filtering and pagination.

	Filters:
	- status: complaint status (Open, Scheduled, In Progress, Flagged, Resolved, Closed)
	- search: text search on complaint name or description
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["description"] = ["like", f"%{search}%"]

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
	}


@frappe.whitelist()
def get_lost_found(
	report_type=None, status=None, search=None, scope="all", page=1, page_size=10
):
	"""Return lost and found items with filtering and pagination.

	Filters:
	- report_type: Lost or Found
	- status: Open, Returned, Closed
	- search: text search on item_name or description
	- scope: "all" or "mine" (filter by current user's App User)
	- page: page number (1-based)
	- page_size: items per page
	"""
	filters = {}

	if report_type and report_type != "All Types":
		filters["report_type"] = report_type

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["item_name"] = ["like", f"%{search}%"]

	if scope == "mine":
		user_email = frappe.session.user
		app_user = frappe.db.get_value("App User", {"email": user_email}, "name")
		if app_user:
			filters["reported_by"] = app_user
		else:
			filters["reported_by"] = "__nonexistent__"

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
			"matched_report",
			"returned_to",
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

		if item.returned_to:
			item["returned_to_name"] = frappe.db.get_value(
				"App User", item.returned_to, "full_name"
			) or item.returned_to
		else:
			item["returned_to_name"] = None

	total = frappe.db.count("Lost And Found", filters=filters)

	locations = frappe.db.get_all("Location", fields=["name"], order_by="name asc")

	user_email = frappe.session.user
	current_app_user = frappe.db.get_value("App User", {"email": user_email}, "name")

	return {
		"items": items,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
		"locations": [loc.name for loc in locations],
		"current_app_user": current_app_user,
	}


@frappe.whitelist()
def create_lost_found(
	report_type, item_name, location=None, description=None, image=None
):
	"""Create a lost and found report by the current user."""
	user_email = frappe.session.user
	app_user = frappe.db.get_value("App User", {"email": user_email}, "name")

	if not app_user:
		frappe.throw("No App User found for current session user")

	doc = frappe.get_doc({
		"doctype": "Lost And Found",
		"report_type": report_type,
		"reported_by": app_user,
		"item_name": item_name,
		"location": location,
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
	name, report_type=None, item_name=None, location=None, description=None, image=None
):
	"""Update a lost and found report. Only the owner can edit."""
	user_email = frappe.session.user
	app_user = frappe.db.get_value("App User", {"email": user_email}, "name")

	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only edit your own reports")

	if report_type is not None:
		doc.report_type = report_type
	if item_name is not None:
		doc.item_name = item_name
	if location is not None:
		doc.location = location
	if description is not None:
		doc.description = description
	if image is not None:
		doc.image = image

	doc.save(ignore_permissions=True)

	return {
		"name": doc.name,
		"report_type": doc.report_type,
		"item_name": doc.item_name,
		"status": doc.status,
	}


@frappe.whitelist()
def delete_lost_found(name):
	"""Delete a lost and found report. Only the owner can delete."""
	user_email = frappe.session.user
	app_user = frappe.db.get_value("App User", {"email": user_email}, "name")

	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only delete your own reports")

	frappe.delete_doc("Lost And Found", name, ignore_permissions=True)

	return {"deleted": True, "name": name}


@frappe.whitelist()
def get_events(page=1, page_size=10):
	"""Return upcoming published events, sorted by start_date ascending.

	Only events with start_date >= now and event_status = Published are returned.
	The first event is the next upcoming (highlighted) event.
	"""
	from frappe.utils import now_datetime

	filters = {
		"event_status": "Published",
		"start_date": [">=", now_datetime()],
	}

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
	"""Return current user's profile details from App User and Staff doctypes."""
	user_email = frappe.session.user

	app_user = frappe.db.get_value(
		"App User",
		{"email": user_email},
		["name", "first_name", "last_name", "full_name", "email", "location", "active"],
		as_dict=True,
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
	"""Change the current user's password in App User doctype.

	The App User on_update hook will sync the new password to the linked Frappe User.
	"""
	if not new_password or not confirm_password:
		frappe.throw("Both new password and confirm password are required")

	if new_password != confirm_password:
		frappe.throw("New password and confirm password do not match")

	if len(new_password) < 6:
		frappe.throw("Password must be at least 6 characters long")

	user_email = frappe.session.user
	app_user_name = frappe.db.get_value("App User", {"email": user_email}, "name")

	if not app_user_name:
		frappe.throw("No App User found for current session user")

	doc = frappe.get_doc("App User", app_user_name)
	doc.password = new_password
	doc.save(ignore_permissions=True)

	return {"success": True, "message": "Password changed successfully"}


@frappe.whitelist()
def get_dashboard_stats():
	"""Return comprehensive dashboard statistics for supervisor overview."""
	from frappe.utils import now_datetime, add_days

	now = now_datetime()

	# ── Complaints ──
	complaint_statuses = ["Open", "Scheduled", "In Progress", "Flagged", "Resolved", "Closed"]
	complaint_counts = {}
	for s in complaint_statuses:
		complaint_counts[s] = frappe.db.count("Complaints", {"status": s})
	complaint_total = sum(complaint_counts.values())
	complaint_unsolved = complaint_counts["Open"] + complaint_counts["Scheduled"] + complaint_counts["In Progress"] + complaint_counts["Flagged"]
	complaint_solved = complaint_counts["Resolved"] + complaint_counts["Closed"]
	complaint_resolution_rate = round((complaint_solved / complaint_total * 100), 1) if complaint_total > 0 else 0

	# Complaints in last 7 days (for trend)
	complaints_7d = frappe.db.count("Complaints", {"complaint_date": [">=", add_days(now, -7)]})

	# ── Maintenance Tasks ──
	task_statuses = ["Open", "In Progress", "Flagged", "Overdue", "Completed"]
	task_counts = {}
	for s in task_statuses:
		task_counts[s] = frappe.db.count("Maintenance Task Allocation", {"status": s})
	task_total = sum(task_counts.values())
	task_completed = task_counts["Completed"]
	task_active = task_counts["Open"] + task_counts["In Progress"] + task_counts["Flagged"] + task_counts["Overdue"]
	task_completion_rate = round((task_completed / task_total * 100), 1) if task_total > 0 else 0

	# Technician workload
	technicians = frappe.get_all(
		"Staff",
		filters={"staff_type": "Technician", "active": 1},
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

	# ── Assets ──
	asset_statuses = ["Available", "Allocated", "Under Maintenance", "Damaged", "Decommissioned"]
	asset_counts = {}
	for s in asset_statuses:
		asset_counts[s] = frappe.db.count("Asset", {"status": s})
	asset_total = sum(asset_counts.values())
	asset_active = asset_counts["Available"] + asset_counts["Allocated"]
	asset_decommissioned = asset_counts["Decommissioned"]
	asset_damaged = asset_counts["Damaged"]
	asset_under_maintenance = asset_counts["Under Maintenance"]
	asset_health_rate = round(((asset_total - asset_decommissioned - asset_damaged) / asset_total * 100), 1) if asset_total > 0 else 0

	# ── Members ──
	member_total = frappe.db.count("Member")
	member_active = frappe.db.count("Member", {"active": 1})
	member_inactive = member_total - member_active
	member_flex = frappe.db.count("Member", {"active": 1, "member_type": "Flex"})
	member_regular = frappe.db.count("Member", {"active": 1, "member_type": "Regular"})
	member_active_rate = round((member_active / member_total * 100), 1) if member_total > 0 else 0

	# New members in last 30 days
	new_members_30d = frappe.db.count("Member", {"join_date": [">=", add_days(now, -30)]})

	# ── Parking Slots ──
	parking_statuses = ["Available", "Occupied", "Inactive"]
	parking_counts = {}
	for s in parking_statuses:
		parking_counts[s] = frappe.db.count("Parking Slot", {"status": s, "enabled": 1})
	parking_total = sum(parking_counts.values())
	parking_occupancy_rate = round((parking_counts["Occupied"] / parking_total * 100), 1) if parking_total > 0 else 0

	parking_types = ["Bike", "Car", "Visitor"]
	parking_by_type = {}
	for t in parking_types:
		parking_by_type[t] = {
			"total": frappe.db.count("Parking Slot", {"slot_type": t, "enabled": 1}),
			"available": frappe.db.count("Parking Slot", {"slot_type": t, "enabled": 1, "status": "Available"}),
			"occupied": frappe.db.count("Parking Slot", {"slot_type": t, "enabled": 1, "status": "Occupied"}),
		}

	# ── Lost & Found ──
	lf_open = frappe.db.count("Lost And Found", {"status": "Open"})
	lf_returned = frappe.db.count("Lost And Found", {"status": "Returned"})
	lf_closed = frappe.db.count("Lost And Found", {"status": "Closed"})
	lf_total = lf_open + lf_returned + lf_closed

	# ── Events ──
	event_upcoming = frappe.db.count("Space Event", {"event_status": "Published", "start_date": [">=", now]})
	event_completed = frappe.db.count("Space Event", {"event_status": "Completed"})
	event_draft = frappe.db.count("Space Event", {"event_status": "Draft"})

	latest_event = frappe.db.get_list(
		"Space Event",
		filters={"event_status": "Published", "start_date": [">=", now]},
		fields=["name", "event_name", "event_theme", "location", "start_date", "end_date", "description"],
		order_by="start_date asc",
		limit=1,
	)
	latest_event = latest_event[0] if latest_event else None

	# ── Staff ──
	staff_total = frappe.db.count("Staff", {"active": 1})
	staff_technicians = frappe.db.count("Staff", {"active": 1, "staff_type": "Technician"})
	staff_supervisors = frappe.db.count("Staff", {"active": 1, "staff_type": "Supervisor"})
	staff_security = frappe.db.count("Staff", {"active": 1, "staff_type": "Security"})

	# ── Recent complaints (for scrollable list) ──
	recent_complaints = frappe.db.get_list(
		"Complaints",
		filters={"status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]},
		fields=["name", "status", "complaint_date", "description", "assigned_to"],
		order_by="complaint_date desc",
		limit=5,
	)
	for c in recent_complaints:
		c["assigned_to_name"] = frappe.db.get_value("Staff", c.assigned_to, "full_name") if c.assigned_to else None

	# ── Recent tasks (for scrollable list) ──
	recent_tasks = frappe.db.get_list(
		"Maintenance Task Allocation",
		filters={"status": ["in", ["Open", "In Progress", "Flagged", "Overdue"]]},
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
			"returned": lf_returned,
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
	"""Start work on a maintenance task (Open → In Progress)."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import start_work
	start_work(name)
	return {"success": True, "message": "Work started"}


@frappe.whitelist()
def finish_task(name):
	"""Finish work on a maintenance task (In Progress → Completed)."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import finish_work
	finish_work(name)
	return {"success": True, "message": "Work completed"}


@frappe.whitelist()
def flag_task(name):
	"""Flag a task's asset as unusable (In Progress → Flagged)."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import flag_unusable
	flag_unusable(name)
	return {"success": True, "message": "Asset flagged as unusable, supervisor notified"}


@frappe.whitelist()
def approve_decommission(name, closed_reason=None):
	"""Approve decommission of a flagged task's asset (Flagged → Completed, Asset → Decommissioned)."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import approve_decommission as do_approve
	do_approve(name, closed_reason)
	return {"success": True, "message": "Asset decommissioned"}


@frappe.whitelist()
def reject_flag(name):
	"""Reject a flag and send task back to in progress (Flagged → In Progress)."""
	from smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation import reject_flag as do_reject
	do_reject(name)
	return {"success": True, "message": "Flag rejected, task resumed"}


@frappe.whitelist()
def get_assets(status=None, search=None, page=1, page_size=10):
	"""Return assets with filtering and pagination.

	Filters:
	- status: Asset status (Available, Allocated, Under Maintenance, Damaged, Decommissioned)
	- search: text search on name, serial_number, or asset_item
	"""
	filters = {}

	if status and status != "All Status":
		filters["status"] = status

	if search:
		filters["serial_number"] = ["like", f"%{search}%"]

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