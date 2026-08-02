# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from smartspace.frontend_api.guest import get_space


def get_context(context):
	name = frappe.form_dict.get("name")
	if not name:
		frappe.redirect("/spaces")

	context.space = get_space(name=name)
