# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from smartspace.frontend_api.guest import get_spaces, get_locations, get_floors, get_space_types


def get_context(context):
	context.spaces = get_spaces()
	context.locations = get_locations()
	context.floors = get_floors()
	context.space_types = get_space_types()
