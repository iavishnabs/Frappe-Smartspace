app_name = "smartspace"
app_title = "smartspace"
app_publisher = "avishna"
app_description = "Smart Co working Management System"
app_email = "avishnazenha333@gmail.com"
app_license = "mit"


# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "smartspace",
# 		"logo": "/assets/smartspace/logo.png",
# 		"title": "smartspace",
# 		"route": "/smartspace",
# 		"has_permission": "smartspace.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/smartspace/css/smartspace.css"
# app_include_js = "/assets/smartspace/js/smartspace.js"

# include js, css files in header of web template
# web_include_css = "/assets/smartspace/css/smartspace.css"
# web_include_js = "/assets/smartspace/js/smartspace.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "smartspace/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "smartspace/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "smartspace.utils.jinja_methods",
# 	"filters": "smartspace.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "smartspace.install.before_install"
# after_install = "smartspace.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "smartspace.uninstall.before_uninstall"
# after_uninstall = "smartspace.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "smartspace.utils.before_app_install"
# after_app_install = "smartspace.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "smartspace.utils.before_app_uninstall"
# after_app_uninstall = "smartspace.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "smartspace.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Notification Log": {
		"after_insert": "smartspace.notification.on_notification_log_insert"
	},
	"Lost And Found": {
		"after_insert": "smartspace.notification.on_lost_found_insert"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"smartspace.space_booking.doctype.reservation.reservation.expire_bookings",
		"smartspace.space_event.doctype.space_event.space_event.close_expired_events",
		"smartspace.space_asset.doctype.asset_allocation.asset_allocation.expire_asset_allocations",
		"smartspace.space_asset.doctype.asset_allocation.asset_allocation.update_asset_locations"
	]
}

# Testing
# -------

# before_tests = "smartspace.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "smartspace.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "smartspace.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["smartspace.utils.before_request"]
# after_request = ["smartspace.utils.after_request"]

# Job Events
# ----------
# before_job = ["smartspace.utils.before_job"]
# after_job = ["smartspace.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"smartspace.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Fixtures
# --------

fixtures = [
    {"dt": "Expense Category", "filters": [["enabled", "=", 1]]},
    {"dt": "Custom HTML Block", "filters": [["name", "=", "Portal Link Button"]]}
]
