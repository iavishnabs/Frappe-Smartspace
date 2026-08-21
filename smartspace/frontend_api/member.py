import frappe
from frappe.utils import now_datetime, today, add_days, flt, get_datetime

from smartspace.frontend_api.auth import (
	get_session_app_user,
	get_session_app_user_doc,
	get_session_user_location,
	get_session_user_role,
)


# ─── Profile ──────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_profile():
	"""Return current member's profile from App User and Member doctypes."""
	app_user = get_session_app_user_doc(
		["name", "first_name", "last_name", "full_name", "email", "location", "active"]
	)
	if not app_user:
		frappe.throw("No App User found for current session user")

	member = frappe.db.get_value(
		"Member",
		{"app_user": app_user.name},
		[
			"name", "full_name", "email", "phone", "member_type",
			"join_date", "expiry_date", "location", "active",
			"vehicle_type", "vehicle_number", "vehicle_numbers",
			"date_of_birth", "gender", "profile_image",
			"address_line_1", "city", "state", "country", "pincode",
		],
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
		"member": None,
	}
	if member:
		profile["member"] = member

	return profile


@frappe.whitelist()
def update_profile(phone=None, date_of_birth=None, gender=None, profile_image=None,
                   address_line_1=None, city=None, state=None, country=None, pincode=None):
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	member_name = frappe.db.exists("Member", {"app_user": app_user})
	if not member_name:
		frappe.throw("No Member record found")

	doc = frappe.get_doc("Member", member_name)

	if phone is not None:
		doc.phone = phone
	if date_of_birth is not None:
		doc.date_of_birth = date_of_birth if date_of_birth else None
	if gender is not None:
		doc.gender = gender if gender else None
	if profile_image is not None:
		doc.profile_image = profile_image if profile_image else None
	if address_line_1 is not None:
		doc.address_line_1 = address_line_1
	if city is not None:
		doc.city = city
	if state is not None:
		doc.state = state
	if country is not None:
		doc.country = country if country else None
	if pincode is not None:
		doc.pincode = pincode

	doc.save(ignore_permissions=True)
	return {"success": True, "name": doc.name}


@frappe.whitelist()
def change_password(new_password, confirm_password):
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


# ─── Dashboard ────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_dashboard_stats():
	"""Return dashboard stats for the logged-in member."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	now = now_datetime()
	member = frappe.db.get_value("Member", {"app_user": app_user}, ["name", "member_type", "active"], as_dict=True)

	# Active bookings
	active_bookings = frappe.db.get_list(
		"Reservation",
		filters={"app_user": app_user, "booking_status": ["in", ["Pending", "Booked"]]},
		fields=["name", "space", "booking_type", "booking_from", "booking_to", "booking_status", "total_amount", "payment_status"],
		order_by="booking_from asc",
		limit=5,
	)
	active_booking_count = frappe.db.count("Reservation", {
		"app_user": app_user, "booking_status": ["in", ["Pending", "Booked"]]
	})

	# Compute latest expiry from active reservations
	latest_booking_to = frappe.db.get_value(
		"Reservation",
		filters={"app_user": app_user, "booking_status": ["in", ["Pending", "Booked"]]},
		fieldname="booking_to",
		order_by="booking_to desc",
	)
	if latest_booking_to:
		member["expiry_date"] = get_datetime(latest_booking_to).strftime("%Y-%m-%d")
		days_left = (get_datetime(latest_booking_to) - now).days
		member["days_left"] = max(0, days_left)
	else:
		member["expiry_date"] = None
		member["days_left"] = None

	# Completed bookings
	completed_count = frappe.db.count("Reservation", {
		"app_user": app_user, "booking_status": "Completed"
	})

	# Total spent
	payments = frappe.get_all(
		"Payment",
		filters={"user": app_user, "payment_status": "Paid"},
		pluck="amount",
	)
	total_spent = sum(flt(a) for a in payments)

	# Parking allocations
	parking_count = 0
	if member:
		parking_count = frappe.db.count("Parking Allocation", {
			"member": member.name, "allocation_status": "Active"
		})

	# Complaints
	complaint_open = frappe.db.count("Complaints", {
		"raised_by": frappe.session.user,
		"status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]
	})
	complaint_resolved = frappe.db.count("Complaints", {
		"raised_by": frappe.session.user,
		"status": ["in", ["Resolved", "Closed"]]
	})

	# Events
	user_location = get_session_user_location()
	event_filters = {"event_status": "Published", "start_date": [">=", now]}
	if user_location:
		event_filters["location"] = user_location
	upcoming_events = frappe.db.count("Space Event", event_filters)
	latest_event = frappe.db.get_list(
		"Space Event",
		filters=event_filters,
		fields=["name", "event_name", "event_theme", "location", "start_date", "end_date", "description"],
		order_by="start_date asc",
		limit=1,
	)
	latest_event = latest_event[0] if latest_event else None

	# Lost & Found
	lf_open = frappe.db.count("Lost And Found", {"reported_by": app_user, "status": "Open"})

	return {
		"member": member,
		"active_bookings": active_bookings,
		"active_booking_count": active_booking_count,
		"completed_count": completed_count,
		"total_spent": total_spent,
		"parking_count": parking_count,
		"complaints": {
			"open": complaint_open,
			"resolved": complaint_resolved,
		},
		"events": {
			"upcoming": upcoming_events,
			"latest": latest_event,
		},
		"lost_found_open": lf_open,
	}


# ─── Spaces ───────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_spaces(search=None, space_type=None, page=1, page_size=12):
	"""Return available spaces for member booking.
	Excludes Conference Room and Event Hall (those are booked via chatbot)."""
	filters = {"availability_status": "Available"}

	filters["space_type"] = ["not in", ["Conference Room", "Event Hall"]]

	if space_type and space_type != "All Types":
		filters["space_type"] = space_type

	if search:
		filters["name"] = ["like", f"%{search}%"]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	spaces = frappe.db.get_list(
		"Space",
		filters=filters,
		fields=["name", "space_type", "availability_status", "location", "floor",
				"seating_capacity", "hourly_rate", "description", "amenities"],
		order_by="name asc",
		start=start,
		limit=page_size,
	)

	for s in spaces:
		if s.location:
			s["location_name"] = frappe.db.get_value("Location", s.location, "location_name") or s.location
		if s.floor:
			s["floor_name"] = frappe.db.get_value("Floor", s.floor, "floor_name") or s.floor
		if s.amenities:
			s["amenities_list"] = [a.strip() for a in s.amenities.split(",") if a.strip()]
		else:
			s["amenities_list"] = []

	total = frappe.db.count("Space", filters)

	return {
		"spaces": spaces,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def get_space_detail(space_name):
	"""Return details for a single space."""
	space = frappe.db.get_value(
		"Space", space_name,
		["name", "space_type", "availability_status", "location", "floor",
		 "seating_capacity", "hourly_rate", "description", "amenities"],
		as_dict=True,
	)
	if not space:
		frappe.throw("Space not found")

	if space.location:
		space["location_name"] = frappe.db.get_value("Location", space.location, "location_name") or space.location
	if space.floor:
		space["floor_name"] = frappe.db.get_value("Floor", space.floor, "floor_name") or space.floor
	if space.amenities:
		space["amenities_list"] = [a.strip() for a in space.amenities.split(",") if a.strip()]
	else:
		space["amenities_list"] = []

	hourly = flt(space.hourly_rate)
	space["pricing"] = {
		"hourly": hourly,
		"daily": hourly * 8,
		"weekly": hourly * 40,
		"monthly": hourly * 160,
		"yearly": hourly * 1920,
	}

	return space


# ─── Reservations / Bookings ──────────────────────────────────────────────────


@frappe.whitelist()
def create_reservation(space, booking_type, booking_from, count, parking_details=None,
		phone=None, gender=None, date_of_birth=None,
		address_line_1=None, city=None, state=None, country=None, pincode=None):
	"""Create a new reservation with optional parking details and member profile data.

	Member details (phone, gender, DOB, address, vehicle) are saved to the Member
	doctype if/when it is created during confirmation. If a Member already exists,
	the details are updated.
	"""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	import json
	if isinstance(parking_details, str):
		parking_details = json.loads(parking_details)

	doc = frappe.get_doc({
		"doctype": "Reservation",
		"app_user": app_user,
		"space": space,
		"booking_type": booking_type,
		"booking_from": booking_from,
		"count": int(count),
		"booking_source": "Manual Booking",
	})

	if parking_details:
		for row in parking_details:
			doc.append("parking_details", {
				"vehicle_type": row.get("vehicle_type"),
				"vehicle_number": row.get("vehicle_number"),
			})

	doc.insert(ignore_permissions=True)

	# Save member details to existing Member (if any) for immediate use
	member_name = frappe.db.exists("Member", {"app_user": app_user})
	if member_name:
		member_updates = {}
		if phone: member_updates["phone"] = phone
		if gender: member_updates["gender"] = gender
		if date_of_birth: member_updates["date_of_birth"] = date_of_birth
		if address_line_1: member_updates["address_line_1"] = address_line_1
		if city: member_updates["city"] = city
		if state: member_updates["state"] = state
		if country: member_updates["country"] = country
		if pincode: member_updates["pincode"] = pincode
		if parking_details:
			vehicle_numbers = ", ".join([r.get("vehicle_number", "") for r in parking_details if r.get("vehicle_number")])
			if vehicle_numbers:
				member_updates["vehicle_numbers"] = vehicle_numbers
		if member_updates:
			frappe.db.set_value("Member", member_name, member_updates)

	# Store member details in frappe.flags so confirm_reservation can pick them up
	vehicle_numbers = ""
	if parking_details:
		vehicle_numbers = ", ".join([r.get("vehicle_number", "") for r in parking_details if r.get("vehicle_number")])
	frappe.flags.member_details = {
		"phone": phone, "gender": gender, "date_of_birth": date_of_birth,
		"address_line_1": address_line_1, "city": city, "state": state,
		"country": country, "pincode": pincode,
		"vehicle_numbers": vehicle_numbers,
	}

	return {
		"success": True,
		"message": "Reservation created successfully",
		"reservation": doc.name,
		"total_amount": doc.total_amount,
		"booking_status": doc.booking_status,
	}


@frappe.whitelist()
def renew_reservation(reservation_name, booking_type, booking_from, count, parking_details=None):
	"""Renew an expired reservation by creating a new one for the same space.

	Only booking details and parking are collected; member profile is reused.
	The space must be available (not occupied) to renew.
	"""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	old = frappe.db.get_value(
		"Reservation", reservation_name,
		["name", "app_user", "space", "booking_status"],
		as_dict=True,
	)
	if not old:
		frappe.throw("Reservation not found")
	if old.app_user != app_user:
		frappe.throw("You can only renew your own bookings")

	# Check space availability
	space_status = frappe.db.get_value("Space", old.space, "availability_status")
	if space_status == "Occupied":
		frappe.throw("This space is currently occupied and cannot be renewed")

	import json
	if isinstance(parking_details, str):
		parking_details = json.loads(parking_details)

	doc = frappe.get_doc({
		"doctype": "Reservation",
		"app_user": app_user,
		"space": old.space,
		"booking_type": booking_type,
		"booking_from": booking_from,
		"count": int(count),
		"booking_source": "Renewal",
	})

	if parking_details:
		for row in parking_details:
			doc.append("parking_details", {
				"vehicle_type": row.get("vehicle_type"),
				"vehicle_number": row.get("vehicle_number"),
			})

	doc.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Renewal reservation created successfully",
		"reservation": doc.name,
		"total_amount": doc.total_amount,
		"booking_status": doc.booking_status,
	}


@frappe.whitelist()
def get_my_bookings(status=None, page=1, page_size=10):
	"""Return the current member's reservations."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	filters = {"app_user": app_user}
	if status and status != "All Status":
		filters["booking_status"] = status

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	bookings = frappe.db.get_list(
		"Reservation",
		filters=filters,
		fields=["name", "space", "booking_type", "booking_from", "booking_to",
				"booking_status", "total_amount", "payment_status", "payment",
				"booking_date", "duration", "count"],
		order_by="booking_from desc",
		start=start,
		limit=page_size,
	)

	for b in bookings:
		if b.space:
			space_type = frappe.db.get_value("Space", b.space, "space_type")
			b["space_type"] = space_type

	total = frappe.db.count("Reservation", filters)

	return {
		"bookings": bookings,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def get_booking_detail(reservation_name):
	"""Return full details for a reservation including space, assets, parking."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	reservation = frappe.db.get_value(
		"Reservation", reservation_name,
		["name", "space", "booking_type", "booking_from", "booking_to",
		 "booking_status", "total_amount", "payment_status", "payment",
		 "booking_date", "duration", "count", "member_type"],
		as_dict=True,
	)
	if not reservation:
		frappe.throw("Reservation not found")

	# Verify ownership
	reservation_app_user = frappe.db.get_value("Reservation", reservation_name, "app_user")
	if reservation_app_user != app_user:
		frappe.throw("You can only view your own bookings")

	# Space details
	if reservation.space:
		space = frappe.db.get_value(
			"Space", reservation.space,
			["name", "space_type", "location", "floor", "seating_capacity",
			 "hourly_rate", "description", "amenities", "availability_status"],
			as_dict=True,
		)
		if space:
			if space.location:
				space["location_name"] = frappe.db.get_value("Location", space.location, "location_name") or space.location
			if space.floor:
				space["floor_name"] = frappe.db.get_value("Floor", space.floor, "floor_name") or space.floor
			if space.amenities:
				space["amenities_list"] = [a.strip() for a in space.amenities.split(",") if a.strip()]
			else:
				space["amenities_list"] = []
		reservation["space_detail"] = space

		# Assets allocated to this space
		asset_allocations = frappe.get_all(
			"Asset Allocation",
			filters={"space": reservation.space, "allocation_status": "Active", "docstatus": 1},
			pluck="name",
		)
		assets = []
		for alloc_name in asset_allocations:
			alloc_items = frappe.db.get_all(
				"Asset Allocation Item",
				filters={"parent": alloc_name},
				pluck="asset",
			)
			for asset_name in alloc_items:
				asset = frappe.db.get_value(
					"Asset", asset_name,
					["name", "serial_number", "asset_item", "status", "location"],
					as_dict=True,
				)
				if asset:
					if asset.asset_item:
						asset["asset_item_name"] = frappe.db.get_value("Asset Item", asset.asset_item, "item_name") or asset.asset_item
					assets.append(asset)
		reservation["assets"] = assets

	# Parking details
	parking_rows = frappe.db.get_all(
		"Reservation Parking",
		filters={"parent": reservation_name},
		fields=["name", "vehicle_type", "vehicle_number", "parking_slot", "parking_allocation"],
	)
	for row in parking_rows:
		if row.parking_slot:
			row["slot_name"] = frappe.db.get_value("Parking Slot", row.parking_slot, "slot_name")
			row["slot_status"] = frappe.db.get_value("Parking Slot", row.parking_slot, "status")
		if row.parking_allocation:
			row["allocation_status"] = frappe.db.get_value("Parking Allocation", row.parking_allocation, "allocation_status")
			row["allocated_from"] = frappe.db.get_value("Parking Allocation", row.parking_allocation, "allocated_from")
	reservation["parking_details"] = parking_rows

	# Payment details
	if reservation.payment:
		payment = frappe.db.get_value(
			"Payment", reservation.payment,
			["name", "payment_method", "amount", "payment_status", "payment_date", "payment_type"],
			as_dict=True,
		)
		reservation["payment_detail"] = payment
	else:
		reservation["payment_detail"] = None

	return reservation


# ─── Payments ─────────────────────────────────────────────────────────────────


@frappe.whitelist()
def pay_for_booking(reservation_name, payment_method="Card"):
	"""Create a payment record for a reservation and mark it as paid (dummy online payment).

	After payment, auto-confirms the reservation: creates Member, sets booking to 'Booked',
	occupies the space, and auto-assigns parking.
	"""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	reservation = frappe.db.get_value(
		"Reservation", reservation_name,
		["name", "app_user", "total_amount", "payment", "payment_status", "booking_status", "space"],
		as_dict=True,
	)
	if not reservation:
		frappe.throw("Reservation not found")
	if reservation.app_user != app_user:
		frappe.throw("You can only pay for your own bookings")
	if reservation.payment_status == "Paid":
		frappe.throw("This booking is already paid")

	if reservation.payment:
		frappe.db.set_value("Payment", reservation.payment, {
			"payment_status": "Paid",
			"payment_method": payment_method,
			"payment_date": now_datetime(),
		})
		payment_name = reservation.payment
	else:
		payment = frappe.get_doc({
			"doctype": "Payment",
			"payment_type": "Receive",
			"user": app_user,
			"amount": reservation.total_amount,
			"payment_status": "Paid",
			"payment_method": payment_method,
			"payment_purpose": f"Space Booking - {reservation.name}",
			"transaction_reference": "Reservation",
			"reference_name": reservation.name,
			"payment_date": now_datetime(),
		})
		payment.insert(ignore_permissions=True)
		payment_name = payment.name

	frappe.db.set_value("Reservation", reservation_name, {
		"payment": payment_name,
		"payment_status": "Paid",
	})

	# Auto-confirm: create Member, set Booked, occupy space, auto-assign parking
	if reservation.booking_status == "Pending":
		from smartspace.space_booking.doctype.reservation.reservation import confirm_reservation
		confirm_reservation(reservation_name)

	return {
		"success": True,
		"message": "Payment successful",
		"payment": payment_name,
		"reservation": reservation_name,
	}


@frappe.whitelist()
def get_transactions(page=1, page_size=20):
	"""Return all payment transactions for the current member (space + event funds)."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	payments = frappe.db.get_list(
		"Payment",
		filters={"user": app_user},
		fields=["name", "payment_type", "payment_purpose", "payment_method",
				"amount", "payment_status", "payment_date",
				"transaction_reference", "reference_name"],
		order_by="payment_date desc",
		start=start,
		limit=page_size,
	)

	for p in payments:
		p["is_event_fund"] = 0
		if p.transaction_reference == "Member Event Fund" and p.reference_name:
			mef = frappe.db.get_value("Member Event Fund", p.reference_name, ["event", "amount"], as_dict=True)
			if mef:
				p["is_event_fund"] = 1
				p["event_name"] = frappe.db.get_value("Space Event", mef.event, "event_name") if mef.event else None
		elif p.transaction_reference == "Reservation" and p.reference_name:
			space = frappe.db.get_value("Reservation", p.reference_name, "space")
			p["space_name"] = space

	total = frappe.db.count("Payment", {"user": app_user})

	return {
		"transactions": payments,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


# ─── Parking ──────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_my_parking():
	"""Return active parking allocations for the current member."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	member = frappe.db.get_value("Member", {"app_user": app_user}, "name")

	allocations = frappe.db.get_list(
		"Parking Allocation",
		filters={"member": member, "allocation_status": "Active"} if member else {"app_user": app_user, "allocation_status": "Active"},
		fields=["name", "parking_slot", "vehicle_number", "allocation_type",
				"allocated_from", "allocated_to", "allocation_status", "reservation"],
		order_by="allocated_from desc",
	)

	for a in allocations:
		if a.parking_slot:
			slot = frappe.db.get_value("Parking Slot", a.parking_slot, ["slot_name", "slot_type", "location", "floor"], as_dict=True)
			if slot:
				a["slot_name"] = slot.slot_name
				a["slot_type"] = slot.slot_type
				a["location"] = slot.location
				a["floor"] = slot.floor

	return {"allocations": allocations}


# ─── Events & Funding ─────────────────────────────────────────────────────────


@frappe.whitelist()
def get_events(page=1, page_size=10):
	"""Return upcoming published events for the member."""
	user_location = get_session_user_location()
	filters = {"event_status": "Published", "start_date": [">=", now_datetime()]}
	if user_location:
		filters["location"] = user_location

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	events = frappe.db.get_list(
		"Space Event",
		filters=filters,
		fields=["name", "event_name", "location", "event_theme", "event_status",
				"start_date", "end_date", "description", "total_collected",
				"total_spent", "fund_balance"],
		order_by="start_date asc",
		start=start,
		limit=page_size,
	)

	for e in events:
		if e.location:
			e["location_name"] = frappe.db.get_value("Location", e.location, "location_name") or e.location
		event_fund = frappe.db.get_value("Event Fund", {"event": e.name}, "name")
		e["event_fund"] = event_fund

	total = frappe.db.count("Space Event", filters)

	return {
		"events": events,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def fund_event(event_name, amount, payment_method="Card"):
	"""Contribute funds to an event. Creates Member Event Fund + Payment."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	member = frappe.db.get_value("Member", {"app_user": app_user}, "name")
	if not member:
		frappe.throw("You must be a confirmed member to contribute to event funds")

	event_fund = frappe.db.get_value("Event Fund", {"event": event_name})
	if not event_fund:
		frappe.throw("No event fund found for this event")

	end_date = frappe.db.get_value("Space Event", event_name, "end_date")
	if end_date and get_datetime(end_date) < now_datetime():
		frappe.throw("This event has ended. Funding is closed.")

	amount = flt(amount)
	if amount <= 0:
		frappe.throw("Amount must be greater than zero")

	# Create payment
	payment = frappe.get_doc({
		"doctype": "Payment",
		"payment_type": "Receive",
		"user": app_user,
		"amount": amount,
		"payment_status": "Paid",
		"payment_method": payment_method,
		"payment_purpose": f"Event Fund Contribution - {event_name}",
		"transaction_reference": "Member Event Fund",
		"payment_date": now_datetime(),
	})
	payment.insert(ignore_permissions=True)

	# Create member event fund
	mef = frappe.get_doc({
		"doctype": "Member Event Fund",
		"event": event_name,
		"event_fund": event_fund,
		"member": member,
		"payment_on": today(),
		"amount": amount,
		"payment": payment.name,
	})
	mef.insert(ignore_permissions=True)

	# Update payment reference_name
	frappe.db.set_value("Payment", payment.name, "reference_name", mef.name)

	# Update event fund totals
	fund_doc = frappe.get_doc("Event Fund", event_fund)
	fund_doc.total_collection = flt(fund_doc.total_collection) + amount
	fund_doc.fund_balance = flt(fund_doc.total_collection) - flt(fund_doc.total_expense)
	fund_doc.save(ignore_permissions=True)

	# Update Space Event fund fields
	space_event = frappe.get_doc("Space Event", event_name)
	space_event.total_collected = flt(space_event.total_collected) + amount
	space_event.fund_balance = flt(space_event.total_collected) - flt(space_event.total_spent)
	space_event.save(ignore_permissions=True)

	return {
		"success": True,
		"message": "Event fund contribution successful",
		"payment": payment.name,
		"member_event_fund": mef.name,
	}


# ─── Complaints ───────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_complaints(status=None, search=None, page=1, page_size=10):
	filters = {"raised_by": frappe.session.user}

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
		fields=["name", "complaint_type", "raised_by", "related_asset", "location",
				"status", "complaint_date", "description", "attachment",
				"assigned_to", "closed_date", "closed_reason"],
		order_by="complaint_date desc",
		start=start,
		limit=page_size,
	)

	for c in complaints:
		if c.assigned_to:
			c["assigned_to_name"] = frappe.db.get_value("Staff", c.assigned_to, "full_name")
		if c.related_asset:
			c["asset_name"] = frappe.db.get_value("Asset", c.related_asset, "serial_number")

	total = frappe.db.count("Complaints", filters)

	return {
		"complaints": complaints,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def create_complaint(complaint_type, description, related_asset=None, attachment=None):
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

	return {
		"name": doc.name,
		"complaint_type": doc.complaint_type,
		"status": doc.status,
	}


@frappe.whitelist()
def update_complaint(name, complaint_type=None, description=None, related_asset=None, attachment=None):
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
	if description is not None:
		doc.description = description
	if attachment is not None:
		doc.attachment = attachment if attachment else None

	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def delete_complaint(name):
	user_id = frappe.session.user
	doc = frappe.get_doc("Complaints", name)

	if doc.raised_by != user_id:
		frappe.throw("You can only delete your own complaints")
	if doc.status != "Open":
		frappe.throw("Only open complaints can be deleted")

	frappe.delete_doc("Complaints", name, ignore_permissions=True)
	return {"deleted": True, "name": name}


# ─── Lost & Found ─────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_lost_found(search=None, status=None, page=1, page_size=10):
	app_user = get_session_app_user()
	filters = {"reported_by": app_user} if app_user else {}

	if status and status != "All Status":
		filters["status"] = status
	if search:
		filters["item_name"] = ["like", f"%{search}%"]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	items = frappe.db.get_list(
		"Lost And Found",
		filters=filters,
		fields=["name", "report_type", "reported_by", "item_name", "image",
				"location", "status", "reported_date", "description"],
		order_by="reported_date desc",
		start=start,
		limit=page_size,
	)

	total = frappe.db.count("Lost And Found", filters)

	return {
		"items": items,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def create_lost_found(report_type, item_name, description=None, image=None):
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	doc = frappe.get_doc({
		"doctype": "Lost And Found",
		"report_type": report_type,
		"reported_by": app_user,
		"item_name": item_name,
		"location": get_session_user_location(),
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
def update_lost_found(name, report_type=None, item_name=None, description=None, image=None, status=None):
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
		if description is not None:
			doc.description = description
		if image is not None:
			doc.image = image if image else None

	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def delete_lost_found(name):
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
	app_user = get_session_app_user()
	doc = frappe.get_doc("Lost And Found", name)

	if doc.reported_by != app_user:
		frappe.throw("You can only close your own reports")
	if doc.status != "Open":
		frappe.throw("Only open reports can be closed")

	doc.status = "Closed"
	doc.save(ignore_permissions=True)
	return {"success": True, "status": "Closed"}


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


# ─── Chatbot Booking (Conference Room & Event Hall) ──────────────────────────


@frappe.whitelist()
def check_space_availability(space, booking_from, booking_type, count):
	"""Check if a space is available for the requested time slot."""
	from frappe.utils import getdate, add_to_date, flt

	try:
		start_dt = getdate(booking_from)
	except Exception:
		frappe.throw("Invalid date format. Please use YYYY-MM-DD HH:MM")

	c = flt(count)
	if c <= 0:
		frappe.throw("Count must be at least 1")

	# Calculate end datetime based on booking type
	type_hours = {
		"Hourly": 1, "Daily": 24, "Weekly": 24 * 7,
		"Monthly": 24 * 30, "Yearly": 24 * 365
	}
	hours = type_hours.get(booking_type, 1) * c
	end_dt = add_to_date(start_dt, hours=hours)

	# Check for overlapping bookings (not cancelled)
	# First: check bookings that have both booking_from and booking_to
	overlapping = frappe.db.get_all(
		"Reservation",
		filters={
			"space": space,
			"booking_status": ["in", ["Pending", "Booked", "Completed"]],
			"booking_from": ["<", end_dt],
			"booking_to": [">", start_dt],
		},
		fields=["name", "booking_from", "booking_to", "booking_status", "app_user",
				"booking_type", "count"],
		limit=5,
	)

	# Also check bookings without booking_to — compute their end from type+count
	if not overlapping:
		other_bookings = frappe.db.get_all(
			"Reservation",
			filters={
				"space": space,
				"booking_status": ["in", ["Pending", "Booked", "Completed"]],
				"booking_from": ["<", end_dt],
				"booking_to": ["is", "not set"],
			},
			fields=["name", "booking_from", "booking_to", "booking_status", "app_user",
					"booking_type", "count"],
			limit=50,
		)
		for b in other_bookings:
			b_type_hours = type_hours.get(b.get("booking_type") or "Hourly", 1)
			b_end = add_to_date(getdate(b.booking_from), hours=b_type_hours * flt(b.count or 1))
			if b_end > start_dt:
				b.booking_to = str(b_end)
				overlapping.append(b)
				if len(overlapping) >= 5:
					break

	if overlapping:
		conflicts = []
		for b in overlapping:
			user_name = ""
			if b.get("app_user"):
				user_name = frappe.db.get_value("App User", b.app_user, "full_name") or b.app_user
			conflicts.append(
				f"{b.booking_from} to {b.booking_to or 'N/A'} (Status: {b.booking_status}, User: {user_name})"
			)
		return {
			"available": False,
			"conflicts": conflicts,
			"message": f"Space is not available — {len(overlapping)} conflicting booking(s) found.",
			"start": str(start_dt),
			"end": str(end_dt),
		}

	return {
		"available": True,
		"message": "Space is available for the requested time.",
		"start": str(start_dt),
		"end": str(end_dt),
	}


@frappe.whitelist()
def chatbot_create_booking(space, booking_type, booking_from, count, purpose=None, attendees=None):
	"""Create a reservation via chatbot for Conference Room or Event Hall."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	space_type = frappe.db.get_value("Space", space, "space_type")
	if space_type not in ("Conference Room", "Event Hall"):
		frappe.throw("Chatbot booking is only available for Conference Room and Event Hall")

	# Check availability before creating booking
	avail = check_space_availability(space, booking_from, booking_type, count)
	if not avail.get("available"):
		conflict_details = "; ".join(avail.get("conflicts", []))
		return {
			"success": False,
			"message": f"Booking conflict detected. {avail.get('message')} Conflicts: {conflict_details}",
		}

	doc = frappe.get_doc({
		"doctype": "Reservation",
		"app_user": app_user,
		"space": space,
		"booking_type": booking_type,
		"booking_from": booking_from,
		"count": flt(count),
		"booking_source": "AI Assistant",
		"booking_status": "Booked",
		"payment_status": "Free",
		"total_amount": 0,
		"remark": f"Purpose: {purpose or 'N/A'} | Attendees: {attendees or 'N/A'}" if purpose or attendees else None,
	})
	doc.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Booking created via AI Assistant",
		"reservation": doc.name,
		"total_amount": doc.total_amount,
		"booking_status": doc.booking_status,
	}


@frappe.whitelist()
def get_chatbot_spaces(space_type=None):
	"""Return Conference Room and Event Hall spaces available for chatbot booking."""
	filters = {"availability_status": "Available"}

	if space_type and space_type in ("Conference Room", "Event Hall"):
		filters["space_type"] = space_type
	else:
		filters["space_type"] = ["in", ["Conference Room", "Event Hall"]]

	spaces = frappe.db.get_list(
		"Space",
		filters=filters,
		fields=["name", "space_type", "location", "floor", "seating_capacity",
				"hourly_rate", "description", "amenities", "availability_status"],
		order_by="name asc",
	)

	for s in spaces:
		if s.location:
			s["location_name"] = frappe.db.get_value("Location", s.location, "location_name") or s.location
		if s.floor:
			s["floor_name"] = frappe.db.get_value("Floor", s.floor, "floor_name") or s.floor

	return {"spaces": spaces}


# ─── Member AI Chatbot Q&A ──────────────────────────────────────────────────


@frappe.whitelist()
def member_ask_question(question):
	"""Natural language Q&A for members — answers about their bookings, spending, events, etc."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")
	if not question or not question.strip():
		return {"answer": "Please ask a question."}

	q = question.lower().strip()

	# Gather member data
	member = frappe.db.get_value("Member", {"app_user": app_user}, ["name", "member_type", "active"], as_dict=True)

	# Bookings
	all_bookings = frappe.db.get_all(
		"Reservation",
		filters={"app_user": app_user},
		fields=["name", "space", "booking_type", "booking_from", "booking_to",
				"booking_status", "total_amount", "payment_status", "booking_date"],
		order_by="booking_from desc",
		limit=50,
	)
	active_bookings = [b for b in all_bookings if b.get("booking_status") in ("Pending", "Booked")]
	completed_bookings = [b for b in all_bookings if b.get("booking_status") == "Completed"]
	cancelled_bookings = [b for b in all_bookings if b.get("booking_status") == "Cancelled"]

	# Payments
	payments = frappe.get_all(
		"Payment",
		filters={"user": app_user, "payment_status": "Paid"},
		fields=["name", "amount", "payment_date", "payment_method", "reference_name"],
		order_by="payment_date desc",
		limit=50,
	)
	total_spent = sum(flt(p.amount) for p in payments)

	# Parking
	parking_count = 0
	if member:
		parking_count = frappe.db.count("Parking Allocation", {
			"member": member.name, "allocation_status": "Active"
		})

	# Events
	user_location = get_session_user_location()
	event_filters = {"event_status": "Published"}
	if user_location:
		event_filters["location"] = user_location
	upcoming_events = frappe.db.get_all(
		"Space Event",
		filters={**event_filters, "start_date": [">=", now_datetime()]},
		fields=["name", "event_name", "event_theme", "start_date", "end_date", "location"],
		order_by="start_date asc",
		limit=5,
	)

	# Complaints
	complaint_open = frappe.db.count("Complaints", {
		"raised_by": frappe.session.user, "status": ["in", ["Open", "Scheduled", "In Progress", "Flagged"]]
	})
	complaint_resolved = frappe.db.count("Complaints", {
		"raised_by": frappe.session.user, "status": ["in", ["Resolved", "Closed"]]
	})

	# ── Topic detection ──
	topic_keywords = {
		"booking": ["booking", "reservation", "book", "reserve", "slot", "space", "room", "cabin", "conference"],
		"payment": ["payment", "paid", "spend", "spent", "transaction", "cost", "amount", "bill", "invoice", "money", "rupees", "rs"],
		"event": ["event", "gather", "meetup", "party", "celebration", "function", "theme", "community"],
		"parking": ["parking", "park", "vehicle", "car", "bike", "slot"],
		"complaint": ["complaint", "issue", "problem", "grievance", "report"],
		"profile": ["profile", "account", "member", "details", "my info", "my details", "who am i"],
		"overview": ["overview", "summary", "dashboard", "status", "all", "everything", "brief", "report"],
	}

	scores = {}
	for topic, keywords in topic_keywords.items():
		score = 0
		for kw in keywords:
			if kw in q:
				score += len(kw.split())
		if score > 0:
			scores[topic] = score

	if not scores:
		generic_words = ["what", "how", "show", "tell", "give", "see", "view", "info", "information", "data", "share", "details"]
		if any(w in q for w in generic_words):
			scores["overview"] = 1
		else:
			return {
				"answer": (
					"I can help you with:\n"
					"• Your bookings and reservations\n"
					"• Payment history and spending\n"
					"• Upcoming events\n"
					"• Parking allocations\n"
					"• Complaints status\n"
					"• Your profile details\n\n"
					"Try: \"What are my active bookings?\" or \"How much have I spent?\""
				)
			}

	top_topics = [t[0] for t in sorted(scores.items(), key=lambda x: x[1], reverse=True)]
	if len(top_topics) > 1 and "overview" in top_topics:
		top_topics.remove("overview")

	answer_parts = []

	# ── Booking ──
	if "booking" in top_topics:
		parts = []
		parts.append(f"You have {len(all_bookings)} total bookings ({len(active_bookings)} active, {len(completed_bookings)} completed, {len(cancelled_bookings)} cancelled).")
		if active_bookings:
			parts.append("Active bookings:")
			for b in active_bookings[:3]:
				space_name = frappe.db.get_value("Space", b.space, "name") or b.space if b.space else "N/A"
				parts.append(f"  • {space_name} — {b.booking_type} from {b.booking_from} (Status: {b.booking_status}, ₹{flt(b.total_amount or 0):,.0f})")
		else:
			parts.append("No active bookings right now.")
		if completed_bookings:
			parts.append(f"Last completed: {frappe.db.get_value('Space', completed_bookings[0].space, 'name') or 'N/A'} on {completed_bookings[0].booking_from}")
		answer_parts.append("\n".join(parts))

	# ── Payment ──
	if "payment" in top_topics:
		parts = [f"You've spent a total of ₹{total_spent:,.0f} across {len(payments)} payments."]
		if payments:
			parts.append("Recent payments:")
			for p in payments[:3]:
				parts.append(f"  • ₹{flt(p.amount or 0):,.0f} on {p.payment_date} via {p.payment_method}")
		else:
			parts.append("No payment history found.")
		answer_parts.append("\n".join(parts))

	# ── Event ──
	if "event" in top_topics:
		parts = []
		if upcoming_events:
			parts.append(f"{len(upcoming_events)} upcoming event(s) at your location:")
			for e in upcoming_events[:3]:
				loc_name = frappe.db.get_value("Location", e.location, "location_name") if e.location else "N/A"
				parts.append(f"  • {e.event_name} — {e.start_date} at {loc_name}")
		else:
			parts.append("No upcoming events at your location right now.")
		answer_parts.append("\n".join(parts))

	# ── Parking ──
	if "parking" in top_topics:
		if parking_count > 0:
			answer_parts.append(f"You have {parking_count} active parking allocation(s).")
		else:
			answer_parts.append("You have no active parking allocations. Parking is auto-assigned when you confirm a booking.")

	# ── Complaint ──
	if "complaint" in top_topics:
		parts = [f"You have {complaint_open} open complaint(s) and {complaint_resolved} resolved complaint(s)."]
		if complaint_open == 0:
			parts.append("No open complaints — everything looks good!")
		answer_parts.append("\n".join(parts))

	# ── Profile ──
	if "profile" in top_topics:
		app_user_doc = frappe.db.get_value("App User", app_user, ["full_name", "email", "active"], as_dict=True)
		parts = [f"Name: {app_user_doc.full_name or 'N/A'}"]
		parts.append(f"Email: {app_user_doc.email or 'N/A'}")
		if member:
			parts.append(f"Member Type: {member.member_type or 'N/A'}")
			parts.append(f"Active: {'Yes' if member.active else 'No'}")
		parts.append(f"Total bookings: {len(all_bookings)}")
		parts.append(f"Total spent: ₹{total_spent:,.0f}")
		answer_parts.append("\n".join(parts))

	# ── Overview ──
	if "overview" in top_topics and len(top_topics) == 1:
		parts = [
			f"Here's your overview:",
			f"  • Active bookings: {len(active_bookings)}",
			f"  • Completed bookings: {len(completed_bookings)}",
			f"  • Total spent: ₹{total_spent:,.0f}",
			f"  • Parking: {parking_count} active",
			f"  • Upcoming events: {len(upcoming_events)}",
			f"  • Open complaints: {complaint_open}",
		]
		answer_parts.append("\n".join(parts))

	return {"answer": "\n\n".join(answer_parts) if answer_parts else "I couldn't understand your question. Try asking about your bookings, payments, events, parking, or complaints."}
