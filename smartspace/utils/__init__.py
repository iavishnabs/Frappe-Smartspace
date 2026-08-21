import frappe


def add_analytics_shortcut():
	"""Add Analytics Portal shortcut to Smart Space Master workspace."""
	workspace_name = "Smart Space Master"

	if not frappe.db.exists("Workspace", workspace_name):
		print(f"Workspace '{workspace_name}' not found")
		return

	# Check if shortcut already exists
	existing = frappe.db.exists("Workspace Shortcut", {
		"parent": workspace_name,
		"label": "Analytics Portal",
	})
	if existing:
		print("Analytics Portal shortcut already exists")
		return

	workspace = frappe.get_doc("Workspace", workspace_name)
	workspace.append("shortcuts", {
		"type": "URL",
		"label": "Analytics Portal",
		"url": "/admin-portal/analytics",
		"icon": "bar-chart",
		"color": "Blue",
	})
	workspace.save(ignore_permissions=True)
	frappe.db.commit()
	print("Analytics Portal shortcut added successfully")
