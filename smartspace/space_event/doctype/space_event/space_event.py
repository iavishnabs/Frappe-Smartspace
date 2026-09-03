# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document


class SpaceEvent(Document):
	def on_update(self):
		self.update_event_summary()


	def update_event_summary(self):
		total_collected = frappe.db.sql("""
			SELECT COALESCE(SUM(mef.amount), 0)
			FROM `tabMember Event Fund` mef
			JOIN `tabEvent Fund` ef ON mef.event_fund = ef.name
			WHERE ef.event = %s
		""", (self.name,))[0][0]

		total_spent = frappe.db.sql("""
			SELECT COALESCE(SUM(e.net_amount), 0)
			FROM `tabExpense` e
			WHERE e.event = %s AND e.status = 'Approved'
		""", (self.name,))[0][0]

		fund_balance = total_collected - total_spent

		frappe.db.set_value("Space Event", self.name, {
			"total_collected": total_collected,
			"total_spent": total_spent,
			"fund_balance": fund_balance
		})


@frappe.whitelist()
def publish_event(name):
	event = frappe.get_doc("Space Event", name)
	if event.event_status != "Draft":
		frappe.throw("Only draft events can be published")

	event.event_status = "Published"
	event.published = 1
	event.save(ignore_permissions=True)

	notify_members_and_staff(event)
	return "Published"


def notify_members_and_staff(event):
	from smartspace.notification import create_notification_log

	subject = f"New Event: {event.event_name}"
	event_location = event.location

	if not event_location:
		return

	notified_users = set()

	members = frappe.get_all("Member", filters={"active": 1}, fields=["app_user", "name"])
	for member in members:
		if not member.app_user:
			continue
		au_location = frappe.db.get_value("App User", member.app_user, "location")
		if au_location != event_location:
			continue
		user = frappe.db.get_value("App User", member.app_user, "user")
		if not user or user in notified_users:
			continue
		create_notification_log(
			subject=subject,
			for_user=user,
			document_type="Space Event",
			document_name=event.name,
		)
		notified_users.add(user)

	members_with_bookings = frappe.db.sql("""
		SELECT DISTINCT au.user
		FROM `tabReservation` r
		JOIN `tabSpace` s ON r.space = s.name
		JOIN `tabApp User` au ON r.app_user = au.name
		WHERE s.location = %s
		AND r.booking_status = 'Booked'
		AND au.user IS NOT NULL
	""", (event_location,), as_dict=True)
	for row in members_with_bookings:
		if row.user in notified_users:
			continue
		create_notification_log(
			subject=subject,
			for_user=row.user,
			document_type="Space Event",
			document_name=event.name,
		)
		notified_users.add(row.user)

	staff = frappe.get_all("Staff", filters={"active": 1, "location": event_location}, fields=["app_user"])
	for s in staff:
		if not s.app_user:
			continue
		user = frappe.db.get_value("App User", s.app_user, "user")
		if not user or user in notified_users:
			continue
		create_notification_log(
			subject=subject,
			for_user=user,
			document_type="Space Event",
			document_name=event.name,
		)
		notified_users.add(user)


@frappe.whitelist()
def close_expired_events():
	events = frappe.get_all(
		"Space Event",
		filters={"event_status": "Published", "end_date": ["<", now_datetime()]},
		pluck="name"
	)
	for name in events:
		frappe.db.set_value("Space Event", name, "event_status", "Completed")
