# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist(allow_guest=True)
def get_spaces(space_type=None, location=None, floor=None, search=None):
	"""Return list of spaces with details for public browsing.

	Optional filters:
	- space_type: Desk, Cabin, Conference Room, Meeting Room, Private Office, Event Hall
	- location: Location name
	- floor: Floor name
	- search: text search on space name or description
	"""
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

	# Enrich with location and floor display names
	for space in spaces:
		if space.get("location"):
			space["location_name"] = frappe.db.get_value("Location", space["location"], "location_name")
		if space.get("floor"):
			space["floor_name"] = frappe.db.get_value("Floor", space["floor"], "floor_name")

	return spaces


@frappe.whitelist(allow_guest=True)
def get_space(name):
	"""Return full details of a single space for the detail page."""
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

	# Enrich with display names
	if space.get("location"):
		space["location_name"] = frappe.db.get_value("Location", space["location"], "location_name")
	if space.get("floor"):
		space["floor_name"] = frappe.db.get_value("Floor", space["floor"], "floor_name")

	# Derived pricing breakdown
	hourly_rate = float(space.get("hourly_rate") or 0)
	space["pricing"] = {
		"hourly": hourly_rate,
		"daily": hourly_rate * 8,
		"weekly": hourly_rate * 40,
		"monthly": hourly_rate * 160,
		"yearly": hourly_rate * 1920,
	}

	# Amenities as list
	if space.get("amenities"):
		space["amenities_list"] = [a.strip() for a in space["amenities"].split(",") if a.strip()]
	else:
		space["amenities_list"] = []

	return space


@frappe.whitelist(allow_guest=True)
def get_locations():
	"""Return all active locations for filter dropdown."""
	return frappe.get_all(
		"Location",
		filters={"status": "Active"},
		fields=["name", "location_name"],
		order_by="location_name asc",
	)


@frappe.whitelist(allow_guest=True)
def get_floors(location=None):
	"""Return distinct floor names with their associated locations for filter dropdown."""
	filters = {"enabled": 1}

	if location and location != "All Locations":
		filters["location"] = location

	floors = frappe.get_all(
		"Floor",
		filters=filters,
		fields=["floor_name", "location"],
		order_by="floor_name asc",
	)

	# Deduplicate by floor_name, collect all locations per floor name
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
	"""Return all space types that have at least one space."""
	return frappe.db.get_all(
		"Space",
		filters={"availability_status": "Available"},
		fields=["distinct space_type as space_type"],
		order_by="space_type asc",
	)
