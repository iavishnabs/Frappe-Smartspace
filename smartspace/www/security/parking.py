import frappe
from smartspace.frontend_api.auth import require_role


def get_context(context):
	require_role("Security")
