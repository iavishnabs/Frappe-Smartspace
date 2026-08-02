import frappe


@frappe.whitelist(allow_guest=True)
def get_current_user():
	"""Return current logged-in user's info, or None if guest."""
	if frappe.session.user == "Guest":
		return None

	user_email = frappe.session.user

	# Get full_name from Frappe User
	full_name = frappe.db.get_value("User", user_email, "full_name") or user_email

	# Get role and other info from App User
	app_user = frappe.db.get_value(
		"App User",
		{"email": user_email},
		["name", "full_name", "role", "email"],
		as_dict=True,
	)

	if not app_user:
		return {
			"email": user_email,
			"full_name": full_name,
			"role": None,
			"redirect_url": "/home",
		}

	role = app_user.get("role")

	# Map role to dashboard URL
	role_redirects = {
		"Member": "/member/dashboard",
		"Security": "/security/dashboard",
		"Supervisor": "/supervisor/dashboard",
		"Technician": "/technician/dashboard",
		"App Admin": "/app/dashboard",
	}

	redirect_url = role_redirects.get(role, "/home")

	return {
		"email": user_email,
		"full_name": app_user.get("full_name") or full_name,
		"role": role,
		"redirect_url": redirect_url,
	}


@frappe.whitelist()
def logout():
	"""Log out the current user."""
	frappe.local.login_manager.logout()
	return {"message": "Logged out", "redirect_url": "/signin"}


def require_role(required_role):
	"""Check if current user has the required role. Redirect if not.

	Usage in a page's get_context:
		from smartspace.frontend_api.auth import require_role
		require_role("Member")
	"""
	user = get_current_user()

	if not user:
		frappe.redirect("/signin")

	role = user.get("role")

	if role != required_role:
		frappe.redirect(user.get("redirect_url", "/home"))
