# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Event Name"), "fieldname": "event_name", "fieldtype": "Data", "width": 300},
		{"label": _("Event Theme"), "fieldname": "event_theme", "fieldtype": "Data", "width": 150},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Link", "options": "Location", "width": 120},
		{"label": _("Status"), "fieldname": "event_status", "fieldtype": "Data", "width": 100},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Datetime", "width": 140},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Datetime", "width": 140},
		{"label": _("Budget"), "fieldname": "budget_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Collected"), "fieldname": "total_collected", "fieldtype": "Currency", "width": 120},
		{"label": _("Spent"), "fieldname": "total_spent", "fieldtype": "Currency", "width": 120},
		{"label": _("Balance"), "fieldname": "fund_balance", "fieldtype": "Currency", "width": 120},
		{"label": _("Contributors"), "fieldname": "contributors", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions = []
	params = {}

	if filters.get("location"):
		conditions.append("se.location = %(location)s")
		params["location"] = filters["location"]

	if filters.get("event_status"):
		conditions.append("se.event_status = %(event_status)s")
		params["event_status"] = filters["event_status"]

	if filters.get("from_date"):
		conditions.append("se.start_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("se.end_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	where_clause = " AND " + " AND ".join(conditions) if conditions else ""

	results = frappe.db.sql(f"""
		SELECT
			se.name as event_name,
			se.event_theme,
			se.location,
			se.event_status,
			se.start_date,
			se.end_date,
			COALESCE(ef.budget_amount, 0) as budget_amount,
			COALESCE(se.total_collected, 0) as total_collected,
			COALESCE(se.total_spent, 0) as total_spent,
			COALESCE(se.fund_balance, 0) as fund_balance,
			(SELECT COUNT(*) FROM `tabMember Event Fund` mef
			 INNER JOIN `tabEvent Fund` ef2 ON mef.event_fund = ef2.name
			 WHERE ef2.event = se.name) as contributors
		FROM `tabSpace Event` se
		LEFT JOIN `tabEvent Fund` ef ON ef.event = se.name
		WHERE 1=1 {where_clause}
		ORDER BY se.start_date DESC
	""", params, as_dict=True)

	return results
