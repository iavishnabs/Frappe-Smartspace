# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist(allow_guest=True)
def get_spaces(space_type=None, location=None, floor=None, search=None):
	"""Get available spaces."""
	filters = {"availability_status": "Available"}

	if space_type and space_type != "All Types":
		filters["space_type"] = space_type

	if location and location != "All Locations":
		filters["location"] = location

	if floor and floor != "All Floors":
		filters["floor"] = floor

	if search:
		filters["name"] = ["like", f"%{search}%"]

	spaces = frappe.get_all(
		"Space",
		filters=filters,
		fields=[
			"name",
			"space_type",
			"availability_status",
			"seating_capacity",
			"location",
			"floor",
			"hourly_rate",
			"amenities",
			"description",
		],
		order_by="name asc",
	)

	# add location and floor display names
	for space in spaces:
		if space.get("location"):
			space["location_name"] = frappe.db.get_value("Location", space["location"], "location_name")
		if space.get("floor"):
			space["floor_name"] = frappe.db.get_value("Floor", space["floor"], "floor_name")

	return spaces


@frappe.whitelist(allow_guest=True)
def get_space(name):
	"""Get space details."""
	if not name:
		frappe.throw("Space name is required")

	if not frappe.db.exists("Space", name):
		frappe.throw("Space not found", frappe.NotFound)

	space = frappe.db.get_value(
		"Space",
		name,
		[
			"name",
			"space_type",
			"availability_status",
			"seating_capacity",
			"location",
			"floor",
			"hourly_rate",
			"amenities",
			"description",
		],
		as_dict=True,
	)

	# add display names
	if space.get("location"):
		space["location_name"] = frappe.db.get_value("Location", space["location"], "location_name")
	if space.get("floor"):
		space["floor_name"] = frappe.db.get_value("Floor", space["floor"], "floor_name")

	# pricing breakdown
	hourly_rate = float(space.get("hourly_rate") or 0)
	space["pricing"] = {
		"hourly": hourly_rate,
		"daily": hourly_rate * 8,
		"weekly": hourly_rate * 40,
		"monthly": hourly_rate * 160,
		"yearly": hourly_rate * 1920,
	}

	# amenities as list
	if space.get("amenities"):
		space["amenities_list"] = [a.strip() for a in space["amenities"].split(",") if a.strip()]
	else:
		space["amenities_list"] = []

	return space


@frappe.whitelist(allow_guest=True)
def get_locations():
	"""Get active locations."""
	return frappe.get_all(
		"Location",
		filters={"status": "Active"},
		fields=["name", "location_name"],
		order_by="location_name asc",
	)


@frappe.whitelist(allow_guest=True)
def get_floors(location=None):
	"""Get floor names."""
	filters = {"enabled": 1}

	if location and location != "All Locations":
		filters["location"] = location

	floors = frappe.get_all(
		"Floor",
		filters=filters,
		fields=["floor_name", "location"],
		order_by="floor_name asc",
	)

	# deduplicate by floor name, collect locations per floor
	seen = {}
	for flr in floors:
		fname = flr["floor_name"]
		if fname not in seen:
			seen[fname] = {"floor_name": fname, "locations": []}
		if flr.get("location") and flr["location"] not in seen[fname]["locations"]:
			seen[fname]["locations"].append(flr["location"])

	return list(seen.values())


@frappe.whitelist(allow_guest=True)
def get_space_types():
	"""Get space types."""
	return frappe.db.get_all(
		"Space",
		filters={"availability_status": "Available"},
		fields=["distinct space_type as space_type"],
		order_by="space_type asc",
	)
