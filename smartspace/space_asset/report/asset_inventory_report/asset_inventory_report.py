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
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 180},
		{"label": _("Asset Item"), "fieldname": "asset_item", "fieldtype": "Link", "options": "Asset Item", "width": 180},
		{"label": _("Asset Type"), "fieldname": "asset_type", "fieldtype": "Data", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Count"), "fieldname": "asset_count", "fieldtype": "Int", "width": 80},
		{"label": _("Total Value"), "fieldname": "total_value", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = []
	params = {}

	if filters.get("location"):
		conditions.append("a.location = %(location)s")
		params["location"] = filters["location"]

	if filters.get("status"):
		conditions.append("a.status = %(status)s")
		params["status"] = filters["status"]

	if filters.get("asset_type"):
		conditions.append("ai.asset_type = %(asset_type)s")
		params["asset_type"] = filters["asset_type"]

	where_clause = " AND " + " AND ".join(conditions) if conditions else ""

	results = frappe.db.sql(f"""
		SELECT
			a.location as location,
			a.asset_item as asset_item,
			ai.asset_type as asset_type,
			a.status as status,
			COUNT(*) as asset_count,
			COALESCE(SUM(a.unit_cost), 0) as total_value
		FROM `tabAsset` a
		LEFT JOIN `tabAsset Item` ai ON ai.name = a.asset_item
		WHERE 1=1 {where_clause}
		GROUP BY a.location, a.asset_item, ai.asset_type, a.status
		ORDER BY a.location, a.asset_item, a.status
	""", params, as_dict=True)

	return results
