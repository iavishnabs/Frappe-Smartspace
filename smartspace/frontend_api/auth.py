import frappe
import re


def get_session_user_location():
	"""Return the location of the current session user's App User record.

	frappe.session.user is the User doctype ID, which matches the `user` Link field on App User.
	Falls back to `email` field if needed.
	Returns None if no App User or location is found.
	"""
	user_id = frappe.session.user
	loc = frappe.db.get_value("App User", {"user": user_id}, "location")
	if not loc:
		loc = frappe.db.get_value("App User", {"email": user_id}, "location")
	return loc


def get_session_app_user():
	"""Return the App User name for the current session user.

	Looks up by `user` Link field first, then `email` field.
	Returns None if no App User is found.
	"""
	user_id = frappe.session.user
	app_user = frappe.db.get_value("App User", {"user": user_id}, "name")
	if not app_user:
		app_user = frappe.db.get_value("App User", {"email": user_id}, "name")
	return app_user


def get_session_user_role():
	"""Return the role of the current session user's App User record.

	Returns None if no App User or role is found.
	"""
	user_id = frappe.session.user
	role = frappe.db.get_value("App User", {"user": user_id}, "role")
	if not role:
		role = frappe.db.get_value("App User", {"email": user_id}, "role")
	return role


def is_session_user_admin():
	"""Check if the current session user is Administrator or has App Admin role."""
	user_id = frappe.session.user
	if user_id == "Administrator":
		return True
	role = get_session_user_role()
	return role in ("App Admin", "Administrator")


def get_session_app_user_doc(fields=None):
	"""Return the App User document for the current session user as a dict.

	Looks up by `user` Link field first, then `email` field.
	Returns None if no App User is found.
	"""
	user_id = frappe.session.user
	if fields is None:
		fields = ["name", "first_name", "last_name", "full_name", "email", "location", "active", "role"]
	app_user = frappe.db.get_value("App User", {"user": user_id}, fields, as_dict=True)
	if not app_user:
		app_user = frappe.db.get_value("App User", {"email": user_id}, fields, as_dict=True)
	return app_user


@frappe.whitelist(allow_guest=True)
def get_current_user():
	"""Return current logged-in user's info, or None if guest."""
	if frappe.session.user == "Guest":
		return None

	user_email = frappe.session.user

	# Get full_name from Frappe User
	full_name = frappe.db.get_value("User", user_email, "full_name") or user_email

	# Get role and other info from App User
	app_user = get_session_app_user_doc(["name", "full_name", "role", "email"])

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


@frappe.whitelist(allow_guest=True)
def signup(first_name, last_name, email, password, location=None):
	"""Create a new App User with role Member.

	This is the guest self-signup endpoint. It creates an App User record,
	which triggers the after_insert hook to create a linked Frappe User.
	The Member doctype is NOT created here — it is created when an
	admin/supervisor confirms the user's first reservation.
	"""
	# Validate required fields
	if not first_name or not first_name.strip():
		frappe.throw("First name is required")
	if not email or not email.strip():
		frappe.throw("Email is required")
	if not password or len(password) < 6:
		frappe.throw("Password must be at least 6 characters")

	email = email.strip().lower()

	# Validate email format
	if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
		frappe.throw("Please enter a valid email address")

	# Check if email already exists as App User
	if frappe.db.exists("App User", {"email": email}):
		frappe.throw("An account with this email already exists. Please login instead.")

	# Check if email already exists as Frappe User
	if frappe.db.exists("User", email):
		frappe.throw("An account with this email already exists. Please login instead.")

	# Validate location if provided
	if location:
		if not frappe.db.exists("Location", location):
			frappe.throw("Invalid location selected")

	# Get the Member role
	member_role = frappe.db.get_value("Role", {"role_name": "Member"})
	if not member_role:
		# Create the Member role if it doesn't exist
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
