import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.redirect("/signin")

	roles = frappe.get_roles(frappe.session.user)
	if "App Admin" not in roles and "Administrator" not in roles:
		frappe.local.flags.redirect_location = "/member/dashboard"
		raise frappe.Redirect
