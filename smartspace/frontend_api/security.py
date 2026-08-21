import frappe
from frappe.utils import now_datetime, today, add_days
from smartspace.frontend_api.auth import (
	get_session_app_user,
	get_session_app_user_doc,
	get_session_user_location,
	get_session_user_role,
	is_session_user_admin,
)
from smartspace.notification import create_notification_log

# Reuse technician functions for shared functionality
from smartspace.frontend_api.technician import (
	get_profile as _technician_get_profile,
	change_password as _technician_change_password,
	get_events as _technician_get_events,
	get_lost_found as _technician_get_lost_found,
	create_lost_found as _technician_create_lost_found,
	update_lost_found as _technician_update_lost_found,
	delete_lost_found as _technician_delete_lost_found,
	close_lost_found as _technician_close_lost_found,
	get_complaints as _technician_get_complaints,
	create_complaint as _technician_create_complaint,
	update_complaint as _technician_update_complaint,
	delete_complaint as _technician_delete_complaint,
)


# ─── Profile ─────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_profile():
	return _technician_get_profile()


@frappe.whitelist()
def change_password(new_password, confirm_password):
	return _technician_change_password(new_password, confirm_password)


# ─── Events ──────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_events(page=1, page_size=10):
	return _technician_get_events(page, page_size)


# ─── Lost & Found ─────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_lost_found(report_type=None, status=None, search=None, scope="all", page=1, page_size=10):
	return _technician_get_lost_found(report_type, status, search, scope, page, page_size)


@frappe.whitelist()
def create_lost_found(report_type, item_name, description=None, image=None):
	return _technician_create_lost_found(report_type, item_name, description, image)


@frappe.whitelist()
def update_lost_found(name, report_type=None, item_name=None, description=None, image=None, status=None):
	return _technician_update_lost_found(name, report_type, item_name, description, image, status)


@frappe.whitelist()
def delete_lost_found(name):
	return _technician_delete_lost_found(name)


@frappe.whitelist()
def close_lost_found(name):
	return _technician_close_lost_found(name)


# ─── Complaints ───────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_complaints(status=None, search=None, complaint_type=None, scope="all", page=1, page_size=10):
	return _technician_get_complaints(status, search, complaint_type, scope, page, page_size)


@frappe.whitelist()
def create_complaint(complaint_type, description, related_asset=None, attachment=None):
	return _technician_create_complaint(complaint_type, description, related_asset, attachment)


@frappe.whitelist()
def update_complaint(name, complaint_type=None, description=None, related_asset=None, attachment=None):
	return _technician_update_complaint(name, complaint_type, description, related_asset, attachment)


@frappe.whitelist()
def delete_complaint(name):
	return _technician_delete_complaint(name)


# ─── Members ──────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_members(search=None, member_type=None, page=1, page_size=10):
	"""Return active members filtered by the current security user's location."""
	filters = {"active": 1}

	user_location = get_session_user_location()
	if user_location:
		filters["location"] = user_location

	if search:
		filters["full_name"] = ["like", f"%{search}%"]

	if member_type and member_type != "All Types":
		filters["member_type"] = member_type

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
			"join_date",
			"expiry_date",
			"location",
			"active",
			"profile_image",
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


# ─── Parking Slots ────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_parking_slots(status=None, slot_type=None, search=None, vehicle_search=None, page=1, page_size=10):
	"""Return parking slots filtered by the current security user's location."""
	filters = {"enabled": 1}

	user_location = get_session_user_location()
	if user_location:
		filters["location"] = user_location

	if status and status != "All Status":
		filters["status"] = status

	if slot_type and slot_type != "All Types":
		filters["slot_type"] = slot_type

	if search:
		filters["slot_name"] = ["like", f"%{search}%"]

	# If vehicle_search is provided, find matching parking slots via active allocations
	if vehicle_search:
		matching_slots = frappe.get_all(
			"Parking Allocation",
			filters={
				"vehicle_number": ["like", f"%{vehicle_search}%"],
				"allocation_status": "Active",
			},
			pluck="parking_slot",
		)
		if matching_slots:
			filters["name"] = ["in", matching_slots]
		else:
			filters["name"] = ["in", ["__NO_MATCH__"]]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	slots = frappe.db.get_list(
		"Parking Slot",
		filters=filters,
		fields=["name", "slot_name", "slot_type", "status", "location", "floor", "remarks"],
		order_by="slot_name asc",
		start=start,
		limit=page_size,
	)

	for slot in slots:
		if slot.status == "Occupied":
			allocation = frappe.db.get_value(
				"Parking Allocation",
				{"parking_slot": slot.name, "allocation_status": "Active"},
				["name", "member", "vehicle_number", "app_user", "allocated_from", "allocation_date", "allocation_type", "visitor_name"],
				as_dict=True,
			)
			if allocation:
				slot["allocation"] = allocation
				if allocation.member:
					slot["member_name"] = frappe.db.get_value("Member", allocation.member, "full_name")
				else:
					slot["member_name"] = None
			else:
				slot["allocation"] = None
				slot["member_name"] = None
		else:
			slot["allocation"] = None
			slot["member_name"] = None

	total = frappe.db.count("Parking Slot", filters=filters)

	return {
		"slots": slots,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
	}


@frappe.whitelist()
def assign_parking(parking_slot, vehicle_number, member=None, visitor_name=None, allocation_type=None):
	"""Assign a member or visitor to an available parking slot."""
	slot = frappe.get_doc("Parking Slot", parking_slot)

	if slot.status != "Available":
		frappe.throw("Only available parking slots can be assigned")

	app_user = None
	if member:
		app_user = frappe.db.get_value("Member", member, "app_user")

	if not allocation_type:
		allocation_type = "Visitor" if visitor_name else "Member"

	doc = frappe.get_doc({
		"doctype": "Parking Allocation",
		"parking_slot": parking_slot,
		"vehicle_number": vehicle_number,
		"member": member,
		"app_user": app_user,
		"allocation_type": allocation_type,
		"visitor_name": visitor_name if allocation_type == "Visitor" else None,
	})
	doc.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Parking slot assigned successfully",
		"allocation": doc.name,
	}


@frappe.whitelist()
def release_parking(allocation_name):
	"""Release an active parking allocation."""
	from smartspace.space_parking.doctype.parking_allocation.parking_allocation import release_parking as _release
	result = _release(allocation_name)
	return {"success": True, "message": "Parking slot released successfully"}


# ─── Dashboard ────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_dashboard_stats():
	"""Return dashboard statistics for the logged-in security user."""
	now = now_datetime()
	user_location = get_session_user_location()

	loc_filter = {"location": user_location} if user_location else {}

	# ── Parking Stats ──
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

	# ── Member Stats ──
	member_active = frappe.db.count("Member", {**loc_filter, "active": 1})
	member_flex = frappe.db.count("Member", {**loc_filter, "active": 1, "member_type": "Flex"})
	member_regular = frappe.db.count("Member", {**loc_filter, "active": 1, "member_type": "Regular"})
	new_members_30d = frappe.db.count("Member", {**loc_filter, "active": 1, "join_date": [">=", add_days(today(), -30)]})

	# ── Complaints ──
	complaint_statuses = ["Open", "Scheduled", "In Progress", "Flagged", "Resolved", "Closed"]
	complaint_counts = {}
	for s in complaint_statuses:
		complaint_counts[s] = frappe.db.count("Complaints", {"raised_by": frappe.session.user, "status": s})
	complaint_total = sum(complaint_counts.values())
	complaint_unsolved = complaint_counts["Open"] + complaint_counts["Scheduled"] + complaint_counts["In Progress"] + complaint_counts["Flagged"]

	recent_complaints = frappe.db.get_list(
		"Complaints",
		filters={"raised_by": frappe.session.user, "status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]},
		fields=["name", "status", "complaint_date", "description", "complaint_type"],
		order_by="complaint_date desc",
		limit=5,
	)

	# ── Lost & Found ──
	lf_open = frappe.db.count("Lost And Found", {**loc_filter, "status": "Open"})
	lf_closed = frappe.db.count("Lost And Found", {**loc_filter, "status": "Closed"})

	# ── Events ──
	event_base = {"event_status": "Published", "start_date": [">=", now]}
	if user_location:
		event_base.update(loc_filter)
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
		"parking": {
			"counts": parking_counts,
			"total": parking_total,
			"occupancy_rate": parking_occupancy_rate,
			"by_type": parking_by_type,
		},
		"members": {
			"active": member_active,
			"flex": member_flex,
			"regular": member_regular,
			"new_30d": new_members_30d,
		},
		"complaints": {
			"counts": complaint_counts,
			"total": complaint_total,
			"unsolved": complaint_unsolved,
		},
		"recent_complaints": recent_complaints,
		"lost_found": {
			"open": lf_open,
			"closed": lf_closed,
		},
		"events": {
			"upcoming": event_upcoming,
			"latest": latest_event,
		},
	}


# ─── Notifications ────────────────────────────────────────────────────────────


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
