import frappe
import re


def get_session_user_location():
	"""Get user location."""
	user_id = frappe.session.user
	loc = frappe.db.get_value("App User", {"user": user_id}, "location")
	if not loc:
		loc = frappe.db.get_value("App User", {"email": user_id}, "location")
	return loc


def get_session_app_user():
	"""Get app user name."""
	user_id = frappe.session.user
	app_user = frappe.db.get_value("App User", {"user": user_id}, "name")
	if not app_user:
		app_user = frappe.db.get_value("App User", {"email": user_id}, "name")
	return app_user


def get_session_user_role():
	"""Get user role."""
	user_id = frappe.session.user
	role = frappe.db.get_value("App User", {"user": user_id}, "role")
	if not role:
		role = frappe.db.get_value("App User", {"email": user_id}, "role")
	return role


def is_session_user_admin():
	"""Check admin role."""
	user_id = frappe.session.user
	if user_id == "Administrator":
		return True
	role = get_session_user_role()
	return role in ("App Admin", "Administrator")


def require_active_member():
	"""Check if current member is active, throw if not."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")
	active = frappe.db.get_value("Member", {"app_user": app_user}, "active")
	if active is None:
		frappe.throw("No Member record found")
	if not active:
		frappe.throw("Your membership is inactive. Please book a space to reactivate your membership.")


def require_regular_member():
	"""Check active Regular member."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")
	member_type, active = frappe.db.get_value(
		"Member", {"app_user": app_user}, ["member_type", "active"]
	)
	if member_type is None:
		frappe.throw("No Member record found")
	if not active:
		frappe.throw("Your membership is inactive. Please book a space to reactivate your membership.")
	if member_type != "Regular":
		frappe.throw("AI Booking Assistant is only available for Regular members.")


def get_session_app_user_doc(fields=None):
	"""Get app user doc."""
	user_id = frappe.session.user
	if fields is None:
		fields = ["name", "first_name", "last_name", "full_name", "email", "location", "active", "role"]
	app_user = frappe.db.get_value("App User", {"user": user_id}, fields, as_dict=True)
	if not app_user:
		app_user = frappe.db.get_value("App User", {"email": user_id}, fields, as_dict=True)
	return app_user


@frappe.whitelist(allow_guest=True)
def get_current_user():
	"""Get current user info."""
	if frappe.session.user == "Guest":
		return None

	user_email = frappe.session.user

	full_name = frappe.db.get_value("User", user_email, "full_name") or user_email
	app_user = get_session_app_user_doc(["name", "full_name", "role", "email"])

	if not app_user:
		return {
			"email": user_email,
			"full_name": full_name,
			"role": None,
			"redirect_url": "/home",
		}

	role = app_user.get("role")

	# send each role to their dashboard
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
	"""Logout current user."""
	frappe.local.login_manager.logout()
	return {"message": "Logged out", "redirect_url": "/signin"}


@frappe.whitelist(allow_guest=True)
def signup(first_name, last_name, email, password, location=None):
	"""Guest signup handler."""
	# basic validation
	if not first_name or not first_name.strip():
		frappe.throw("First name is required")
	if not email or not email.strip():
		frappe.throw("Email is required")
	if not password or len(password) < 6:
		frappe.throw("Password must be at least 6 characters")

	email = email.strip().lower()

	# check email format
	if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
		frappe.throw("Please enter a valid email address")

	# make sure email isn't already registered
	if frappe.db.exists("App User", {"email": email}):
		frappe.throw("An account with this email already exists. Please login instead.")

	if frappe.db.exists("User", email):
		frappe.throw("An account with this email already exists. Please login instead.")

	# check location is valid if given
	if location:
		if not frappe.db.exists("Location", location):
			frappe.throw("Invalid location selected")

	member_role = frappe.db.get_value("Role", {"role_name": "Member"})
	if not member_role:
		# create Member role if it doesn't exist yet
		role = frappe.get_doc({
			"doctype": "Role",
			"role_name": "Member",
			"is_custom": 1,
			"desk_access": 0,
		})
		role.insert(ignore_permissions=True)
		member_role = role.name

	app_user = frappe.get_doc({
		"doctype": "App User",
		"first_name": first_name.strip(),
		"last_name": (last_name or "").strip(),
		"email": email,
		"password": password,
		"role": member_role,
		"location": location,
		"active": 1,
	})
	app_user.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Account created successfully. Please login to continue.",
		"email": email,
	}


def require_role(required_role):
	"""Role check decorator."""
	user = get_current_user()

	if not user:
		frappe.redirect("/signin")

	role = user.get("role")

	if role != required_role:
		frappe.redirect(user.get("redirect_url", "/home"))
