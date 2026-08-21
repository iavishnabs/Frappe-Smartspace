# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from smartspace.frontend_api.guest import get_space


def get_context(context):
	name = frappe.form_dict.get("name")
	if not name:
		frappe.redirect("/spaces")

	context.space = get_space(name=name)

	# Check if user is logged in as a member
	if frappe.session.user != "Guest":
		from smartspace.frontend_api.auth import get_current_user
		user = get_current_user()
		if user and user.get("role") == "Member":
			context.book_url = f"/booking-form?space={name}"
		else:
			context.book_url = None
	else:
		context.book_url = None
