import frappe
import json
from frappe.utils import getdate, nowdate, add_days, add_months, get_first_day, get_last_day, cint


def _check_admin_role():
	"""Check admin role."""
	roles = frappe.get_roles(frappe.session.user)
	if "App Admin" not in roles and "Administrator" not in roles:
		frappe.throw("You don't have permission to access this resource.", frappe.PermissionError)


def _get_date_filters(from_date=None, to_date=None):
	"""Get date filters."""
	if not from_date:
		from_date = add_months(getdate(nowdate()), -12)
	if not to_date:
		to_date = getdate(nowdate())
	return getdate(from_date), getdate(to_date)


def _sum(doctype, fieldname, filters=None):
	"""Sum a field."""
	records = frappe.get_all(doctype, filters=filters, fields=[fieldname])
	return sum(r.get(fieldname) or 0 for r in records)


@frappe.whitelist()
def get_analytics_overview(from_date=None, to_date=None, location=None):
	"""Get overview stats."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	# revenue
	payment_filters = {
		"payment_status": "Paid",
		"payment_date": ["between", [fd, td]],
	}
	if location:
		# filter through reservation (no location on Payment)
		space_names = [s.name for s in frappe.get_all("Space", {"location": location}, ["name"])]
		if space_names:
			res_names = [r.name for r in frappe.get_all("Reservation", {"space": ["in", space_names]}, ["name"])]
			if res_names:
				payment_filters["reference_name"] = ["in", res_names]
			else:
				payment_filters["reference_name"] = "__NO_MATCH__"
		else:
			payment_filters["reference_name"] = "__NO_MATCH__"
	total_revenue = _sum("Payment", "amount", filters=payment_filters)

	# bookings
	booking_filters = {
		"booking_date": ["between", [fd, td]],
	}
	if location:
		space_names = [s.name for s in frappe.get_all("Space", {"location": location}, ["name"])]
		if space_names:
			booking_filters["space"] = ["in", space_names]
		else:
			booking_filters["space"] = "__NO_MATCH__"

	total_bookings = frappe.db.count("Reservation", filters=booking_filters)
	pending_bookings = frappe.db.count("Reservation", filters={**booking_filters, "booking_status": "Pending"})
	completed_bookings = frappe.db.count("Reservation", filters={**booking_filters, "booking_status": "Completed"})
	cancelled_bookings = frappe.db.count("Reservation", filters={**booking_filters, "booking_status": "Cancelled"})

	# assets
	asset_filters = {}
	if location:
		asset_filters["location"] = location
	total_assets = frappe.db.count("Asset", filters=asset_filters)
	allocated_assets = frappe.db.count("Asset", filters={**asset_filters, "status": "Allocated"})
	available_assets = frappe.db.count("Asset", filters={**asset_filters, "status": "Available"})
	maintenance_assets = frappe.db.count("Asset", filters={**asset_filters, "status": "Under Maintenance"})
	damaged_assets = frappe.db.count("Asset", filters={**asset_filters, "status": "Damaged"})

	# asset purchase cost
	purchase_filters = {"purchase_date": ["between", [fd, td]]}
	asset_purchase_cost = _sum("Asset", "unit_cost", filters=asset_filters)

	# events
	event_filters = {
		"start_date": ["between", [fd, td]],
	}
	if location:
		event_filters["location"] = location
	total_events = frappe.db.count("Space Event", filters=event_filters)

	# event ratings
	rating_filters = {}
	if from_date or to_date:
		rating_filters["rating_date"] = ["between", [fd, td]]
	all_ratings = frappe.get_all("Event Rating", filters=rating_filters, fields=["rating", "event"])
	if location:
		loc_event_names = set(s.name for s in frappe.get_all("Space Event", {"location": location}, ["name"]))
		all_ratings = [r for r in all_ratings if r.event in loc_event_names]
	total_ratings = len(all_ratings)
	rated_events = len(set(r.event for r in all_ratings))
	avg_event_rating = round(sum(r.rating for r in all_ratings) / total_ratings, 1) if total_ratings else 0

	# vendors
	vendor_purchases = frappe.get_all(
		"Asset Purchase",
		filters={"purchase_date": ["between", [fd, td]], "docstatus": ["<=", 1]},
		fields=["vendor", "net_amount"],
	)
	vendor_count = len(set(p.vendor for p in vendor_purchases if p.vendor))
	vendor_total_spend = sum(p.net_amount or 0 for p in vendor_purchases)

	# members
	member_filters = {"join_date": ["between", [fd, td]]}
	if location:
		member_filters["location"] = location
	total_members = frappe.db.count("Member", filters=member_filters)
	active_members = frappe.db.count("Member", filters={**member_filters, "active": 1})

	return {
		"total_revenue": total_revenue,
		"total_bookings": total_bookings,
		"pending_bookings": pending_bookings,
		"completed_bookings": completed_bookings,
		"cancelled_bookings": cancelled_bookings,
		"total_assets": total_assets,
		"allocated_assets": allocated_assets,
		"available_assets": available_assets,
		"maintenance_assets": maintenance_assets,
		"damaged_assets": damaged_assets,
		"asset_purchase_cost": asset_purchase_cost,
		"total_events": total_events,
		"total_ratings": total_ratings,
		"rated_events": rated_events,
		"avg_event_rating": avg_event_rating,
		"vendor_count": vendor_count,
		"vendor_total_spend": vendor_total_spend,
		"total_members": total_members,
		"active_members": active_members,
		"from_date": str(fd),
		"to_date": str(td),
	}


@frappe.whitelist()
def get_location_wise_stats(from_date=None, to_date=None):
	"""Get location stats."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	locations = frappe.get_all("Location", filters={"status": "Active"}, fields=["name", "location_name"])

	result = []
	for loc in locations:
		loc_name = loc.name

		# spaces
		spaces = frappe.get_all("Space", {"location": loc_name}, ["name", "space_type", "availability_status", "seating_capacity", "hourly_rate"])
		total_spaces = len(spaces)
		available_spaces = len([s for s in spaces if s.availability_status == "Available"])
		occupied_spaces = len([s for s in spaces if s.availability_status == "Occupied"])

		# bookings
		space_names = [s.name for s in spaces] if spaces else []
		if space_names:
			booking_count = frappe.db.count("Reservation", {"space": ["in", space_names], "booking_date": ["between", [fd, td]]})
			booking_revenue = _sum("Reservation", "total_amount", filters={"space": ["in", space_names], "booking_status": ["in", ["Booked", "Completed"]], "booking_date": ["between", [fd, td]]})
		else:
			booking_count = 0
			booking_revenue = 0

		# assets
		assets = frappe.get_all("Asset", {"location": loc_name}, ["name", "status", "unit_cost"])
		total_assets = len(assets)
		allocated_assets = len([a for a in assets if a.status == "Allocated"])
		asset_cost = sum(a.unit_cost or 0 for a in assets)

		# events
		event_count = frappe.db.count("Space Event", {"location": loc_name, "start_date": ["between", [fd, td]]})

		# revenue via reservation (no location on Payment)
		if space_names:
			loc_res_names = [r.name for r in frappe.get_all("Reservation", {"space": ["in", space_names]}, ["name"])]
			if loc_res_names:
				revenue = _sum("Payment", "amount", filters={"payment_status": "Paid", "payment_date": ["between", [fd, td]], "reference_name": ["in", loc_res_names]})
			else:
				revenue = 0
		else:
			revenue = 0

		# members
		member_count = frappe.db.count("Member", {"location": loc_name, "join_date": ["between", [fd, td]]})

		result.append({
			"location": loc_name,
			"location_name": loc.location_name or loc_name,
			"total_spaces": total_spaces,
			"available_spaces": available_spaces,
			"occupied_spaces": occupied_spaces,
			"total_bookings": booking_count,
			"revenue": booking_revenue,
			"total_assets": total_assets,
			"allocated_assets": allocated_assets,
			"asset_cost": asset_cost,
			"total_events": event_count,
			"total_members": member_count,
		})

	return {"locations": result}


@frappe.whitelist()
def get_revenue_trend(from_date=None, to_date=None, location=None, granularity="monthly"):
	"""Get revenue trend."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	payment_filters = {
		"payment_status": "Paid",
		"payment_date": ["between", [fd, td]],
	}
	if location:
		space_names = [s.name for s in frappe.get_all("Space", {"location": location}, ["name"])]
		if space_names:
			res_names = [r.name for r in frappe.get_all("Reservation", {"space": ["in", space_names]}, ["name"])]
			if res_names:
				payment_filters["reference_name"] = ["in", res_names]
			else:
				payment_filters["reference_name"] = "__NO_MATCH__"
		else:
			payment_filters["reference_name"] = "__NO_MATCH__"

	payments = frappe.get_all(
		"Payment",
		filters=payment_filters,
		fields=["payment_date", "amount", "payment_purpose"],
		order_by="payment_date asc",
	)

	# group by month or day
	from collections import OrderedDict
	if granularity == "daily":
		grouped = OrderedDict()
		for p in payments:
			key = str(getdate(p.payment_date))
			grouped[key] = grouped.get(key, 0) + (p.amount or 0)
	else:
		grouped = OrderedDict()
		for p in payments:
			d = getdate(p.payment_date)
			key = f"{d.year}-{d.month:02d}"
			grouped[key] = grouped.get(key, 0) + (p.amount or 0)

	return {
		"labels": list(grouped.keys()),
		"values": list(grouped.values()),
	}


@frappe.whitelist()
def get_booking_trend(from_date=None, to_date=None, location=None, granularity="monthly"):
	"""Get booking trend."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	booking_filters = {
		"booking_date": ["between", [fd, td]],
	}
	if location:
		space_names = [s.name for s in frappe.get_all("Space", {"location": location}, ["name"])]
		if space_names:
			booking_filters["space"] = ["in", space_names]
		else:
			booking_filters["space"] = "__NO_MATCH__"

	bookings = frappe.get_all(
		"Reservation",
		filters=booking_filters,
		fields=["booking_date", "booking_status"],
		order_by="booking_date asc",
	)

	from collections import OrderedDict
	if granularity == "daily":
		grouped = OrderedDict()
		for b in bookings:
			key = str(getdate(b.booking_date))
			if key not in grouped:
				grouped[key] = {"total": 0, "pending": 0, "completed": 0, "cancelled": 0}
			grouped[key]["total"] += 1
			if b.booking_status in grouped[key]:
				grouped[key][b.booking_status.lower()] += 1
	else:
		grouped = OrderedDict()
		for b in bookings:
			d = getdate(b.booking_date)
			key = f"{d.year}-{d.month:02d}"
			if key not in grouped:
				grouped[key] = {"total": 0, "pending": 0, "completed": 0, "cancelled": 0}
			grouped[key]["total"] += 1
			if b.booking_status in grouped[key]:
				grouped[key][b.booking_status.lower()] += 1

	return {
		"labels": list(grouped.keys()),
		"totals": [v["total"] for v in grouped.values()],
		"pending": [v["pending"] for v in grouped.values()],
		"completed": [v["completed"] for v in grouped.values()],
		"cancelled": [v["cancelled"] for v in grouped.values()],
	}


@frappe.whitelist()
def get_space_type_distribution(location=None):
	"""Get space type counts."""
	_check_admin_role()
	filters = {}
	if location:
		filters["location"] = location

	spaces = frappe.get_all("Space", filters=filters, fields=["space_type", "availability_status"])

	from collections import Counter
	type_counts = Counter(s.space_type for s in spaces)

	return {
		"labels": list(type_counts.keys()),
		"values": list(type_counts.values()),
	}


@frappe.whitelist()
def get_asset_status_distribution(location=None):
	"""Get asset status counts."""
	_check_admin_role()
	filters = {}
	if location:
		filters["location"] = location

	assets = frappe.get_all("Asset", filters=filters, fields=["status"])

	from collections import Counter
	status_counts = Counter(a.status for a in assets)

	return {
		"labels": list(status_counts.keys()),
		"values": list(status_counts.values()),
	}


@frappe.whitelist()
def get_vendor_list(from_date=None, to_date=None):
	"""Get vendor summary."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	purchases = frappe.get_all(
		"Asset Purchase",
		filters={"purchase_date": ["between", [fd, td]], "docstatus": ["<=", 1]},
		fields=["name", "vendor", "purchase_date", "net_amount"],
		order_by="purchase_date desc",
	)

	# group by vendor
	from collections import OrderedDict
	vendor_map = OrderedDict()
	for p in purchases:
		vendor = p.vendor or "Unknown"
		if vendor not in vendor_map:
			vendor_map[vendor] = {"vendor": vendor, "total_purchases": 0, "total_amount": 0, "purchases": []}
		vendor_map[vendor]["total_purchases"] += 1
		vendor_map[vendor]["total_amount"] += p.net_amount or 0
		vendor_map[vendor]["purchases"].append({
			"name": p.name,
			"date": str(p.purchase_date) if p.purchase_date else "-",
			"amount": p.net_amount or 0,
		})

	return {"vendors": list(vendor_map.values())}


@frappe.whitelist()
def get_recent_bookings(from_date=None, to_date=None, location=None, limit=20):
	"""Get recent bookings."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	booking_filters = {
		"booking_date": ["between", [fd, td]],
	}
	if location:
		space_names = [s.name for s in frappe.get_all("Space", {"location": location}, ["name"])]
		if space_names:
			booking_filters["space"] = ["in", space_names]
		else:
			booking_filters["space"] = "__NO_MATCH__"

	bookings = frappe.get_all(
		"Reservation",
		filters=booking_filters,
		fields=["name", "space", "app_user", "booking_date", "booking_from",
				"booking_type", "booking_status", "payment_status", "total_amount"],
		order_by="booking_date desc",
		limit=cint(limit),
	)

	# add space and user names
	for b in bookings:
		if b.space:
			space_info = frappe.db.get_value("Space", b.space, ["space_type", "location"], as_dict=True)
			if space_info:
				b.space_type = space_info.space_type
				b.location = space_info.location
		if b.app_user:
			b.user_name = frappe.db.get_value("App User", b.app_user, "full_name") or b.app_user

	return {"bookings": bookings}


@frappe.whitelist()
def get_events_list(from_date=None, to_date=None, location=None):
	"""Get events list."""
	_check_admin_role()
	fd, td = _get_date_filters(from_date, to_date)

	event_filters = {
		"start_date": ["between", [fd, td]],
	}
	if location:
		event_filters["location"] = location

	events = frappe.get_all(
		"Space Event",
		filters=event_filters,
		fields=["name", "event_name", "event_theme", "event_status",
				"start_date", "end_date", "location", "total_collected",
				"total_spent", "fund_balance"],
		order_by="start_date desc",
	)

	for e in events:
		if e.location:
			e.location_name = frappe.db.get_value("Location", e.location, "location_name") or e.location

	return {"events": events}


@frappe.whitelist()
def get_all_locations():
	"""Get all locations."""
	_check_admin_role()
	return frappe.get_all("Location", filters={"status": "Active"}, fields=["name", "location_name"], order_by="location_name asc")
