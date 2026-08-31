# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Organization"), "fieldname": "organization", "fieldtype": "Link", "options": "Organization", "width": 180},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 180},
		{"label": _("Location Status"), "fieldname": "location_status", "fieldtype": "Data", "width": 100},
		{"label": _("Floors"), "fieldname": "floor_count", "fieldtype": "Int", "width": 80},
		{"label": _("Desk"), "fieldname": "desk_count", "fieldtype": "Int", "width": 80},
		{"label": _("Cabin"), "fieldname": "cabin_count", "fieldtype": "Int", "width": 80},
		{"label": _("Conference Room"), "fieldname": "conference_count", "fieldtype": "Int", "width": 120},
		{"label": _("Meeting Room"), "fieldname": "meeting_count", "fieldtype": "Int", "width": 120},
		{"label": _("Private Office"), "fieldname": "office_count", "fieldtype": "Int", "width": 120},
		{"label": _("Event Hall"), "fieldname": "hall_count", "fieldtype": "Int", "width": 100},
		{"label": _("Total Spaces"), "fieldname": "total_spaces", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = []
	params = {}

	if filters.get("organization"):
		conditions.append("loc.organization = %(organization)s")
		params["organization"] = filters["organization"]

	if filters.get("location"):
		conditions.append("loc.name = %(location)s")
		params["location"] = filters["location"]

	if filters.get("location_status"):
		conditions.append("loc.status = %(location_status)s")
		params["location_status"] = filters["location_status"]

	where_clause = " AND " + " AND ".join(conditions) if conditions else ""

	results = frappe.db.sql(f"""
		SELECT
			loc.organization as organization,
			loc.name as location,
			loc.status as location_status,
			(SELECT COUNT(*) FROM `tabFloor` f WHERE f.location = loc.name AND f.enabled = 1) as floor_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Desk') as desk_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Cabin') as cabin_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Conference Room') as conference_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Meeting Room') as meeting_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Private Office') as office_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name AND s.space_type = 'Event Hall') as hall_count,
			(SELECT COUNT(*) FROM `tabSpace` s WHERE s.location = loc.name) as total_spaces
		FROM `tabLocation` loc
		WHERE 1=1 {where_clause}
		ORDER BY loc.organization, loc.location_name
	""", params, as_dict=True)

	return results
