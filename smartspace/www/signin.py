# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from smartspace.frontend_api.auth import get_current_user


def get_context(context):
	# If already logged in, redirect to dashboard
	user = get_current_user()
	if user:
		frappe.redirect(user["redirect_url"])
