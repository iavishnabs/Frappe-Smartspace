# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, today, get_datetime, add_days, add_months, add_years, now_datetime
from datetime import timedelta
from frappe.model.document import Document


class Reservation(Document):
	def validate(self):
		self.set_member_type()
		self.set_booking_details()
		self.validate_office_hours()
		if not self.booking_status:
			self.booking_status = "Pending"

	def on_trash(self):
		if self.space:
			frappe.db.set_value("Space", self.space, "availability_status", "Available")
		release_reservation_parking(self.name)

	def set_member_type(self):
		total_days = self.get_total_booking_days()
		if total_days >= 7:
			self.member_type = "Regular"
		else:
			self.member_type = "Flex"

	def get_total_booking_days(self):
		if not self.booking_type or not self.count:
			return 0
		count = flt(self.count)
		if self.booking_type == "Hourly":
			return count / 8
		elif self.booking_type == "Daily":
			return count
		elif self.booking_type == "Weekly":
			return count * 7
		elif self.booking_type == "Monthly":
			return count * 30
		elif self.booking_type == "Yearly":
			return count * 365
		return 0

	def set_booking_details(self):
		if not self.space or not self.booking_from or not self.count:
			return

		if not self.booking_date:
			self.booking_date = today()

		space_type = frappe.db.get_value("Space", self.space, "space_type")
		hourly_rate = flt(frappe.db.get_value("Space", self.space, "hourly_rate"))
		count = flt(self.count)
		start = get_datetime(self.booking_from)

		if space_type == "Conference Room" and self.booking_type != "Hourly":
			frappe.throw("Conference Room can only be booked on an hourly basis")

		if self.booking_type == "Hourly":
			self.rate = hourly_rate
			self.booking_to = start + timedelta(hours=count)
			self.duration = f"{int(count)} hour(s)"
		elif self.booking_type == "Daily":
			self.rate = hourly_rate * 8
			self.booking_to = add_days(start, count)
			self.duration = f"{int(count)} day(s)"
		elif self.booking_type == "Weekly":
			self.rate = hourly_rate * 40
			self.booking_to = add_days(start, count * 7)
			self.duration = f"{int(count)} week(s)"
		elif self.booking_type == "Monthly":
			self.rate = hourly_rate * 160
			self.booking_to = add_days(start, count * 30)
			self.duration = f"{int(count)} month(s)"
		elif self.booking_type == "Yearly":
			self.rate = hourly_rate * 1920
			self.booking_to = add_days(start, count * 365)
			self.duration = f"{int(count)} year(s)"

		self.total_amount = self.rate * count

		if space_type == "Conference Room":
			is_regular = False
			if self.app_user:
				member_type = frappe.db.get_value("Member", {"app_user": self.app_user}, "member_type")
				if member_type == "Regular":
					is_regular = True
			if is_regular:
				self.total_amount = 0

	def validate_office_hours(self):
		if self.booking_type != "Hourly":
			return
		if not self.booking_from or not self.booking_to:
			return

		start = frappe.db.get_single_value("App Settings", "office_start_time")
		end = frappe.db.get_single_value("App Settings", "office_end_time")
		if not start or not end:
			return

		from_time = get_datetime(self.booking_from).time()
		to_time = get_datetime(self.booking_to).time()

		if from_time < start or to_time > end:
			frappe.throw(f"Hourly bookings are only available between {start} and {end}")

	def create_or_upgrade_member(self):
		if not self.app_user:
			return

		member_details = getattr(frappe.local, 'flags', None)
		member_details = member_details.member_details if member_details and hasattr(member_details, 'member_details') else None
		if not member_details:
			member_details = {}

		existing = frappe.db.exists("Member", {"app_user": self.app_user})
		if existing:
			updates = {}
			current_type = frappe.db.get_value("Member", existing, "member_type")
			if self.member_type == "Regular" and current_type != "Regular":
				updates["member_type"] = "Regular"
				frappe.msgprint("Member upgraded to Regular")
			if not frappe.db.get_value("Member", existing, "active"):
				updates["active"] = 1
				frappe.msgprint("Member reactivated")
			new_expiry = self.booking_to.date() if hasattr(self.booking_to, "date") else self.booking_to
			current_expiry = frappe.db.get_value("Member", existing, "expiry_date")
			if not current_expiry or new_expiry > current_expiry:
				updates["expiry_date"] = new_expiry
			# Apply member details from booking form
			for k in ["phone", "gender", "date_of_birth", "address_line_1", "city", "state", "country", "pincode", "vehicle_numbers"]:
				if member_details.get(k):
					updates[k] = member_details[k]
			if updates:
				frappe.db.set_value("Member", existing, updates)
			return

		app_user = frappe.db.get_value("App User", self.app_user, ["full_name", "user", "location"], as_dict=True)

		member_data = {
			"doctype": "Member",
			"app_user": self.app_user,
			"full_name": app_user.full_name,
			"email": app_user.user,
			"location": app_user.location,
			"member_type": self.member_type,
			"join_date": today(),
			"expiry_date": self.booking_to.date() if hasattr(self.booking_to, "date") else self.booking_to,
			"active": 1
		}

		# Apply member details from booking form
		for k in ["phone", "gender", "date_of_birth", "address_line_1", "city", "state", "country", "pincode", "vehicle_numbers"]:
			if member_details.get(k):
				member_data[k] = member_details[k]

		member = frappe.get_doc(member_data)
		member.insert(ignore_permissions=True)
		frappe.msgprint(f"Member created: {member.name}")


@frappe.whitelist()
def confirm_reservation(name):
	doc = frappe.get_doc("Reservation", name)

	if doc.booking_status != "Pending":
		frappe.throw("Only pending reservations can be confirmed")

	doc.create_or_upgrade_member()

	if doc.total_amount and doc.total_amount > 0 and not doc.payment:
		payment = frappe.get_doc({
			"doctype": "Payment",
			"payment_type": "Receive",
			"user": doc.app_user,
			"amount": doc.total_amount,
			"payment_status": "Pending",
			"payment_method": "Cash",
			"payment_purpose": f"Space Booking - {doc.space}",
			"transaction_reference": "Reservation",
			"reference_name": doc.name
		})
		payment.insert(ignore_permissions=True)
		doc.payment = payment.name
		doc.payment_status = "Pending"
	else:
		doc.payment_status = "Paid"

	doc.booking_status = "Booked"
	doc.save(ignore_permissions=True)

	if doc.space:
		frappe.db.set_value("Space", doc.space, "availability_status", "Occupied")

	auto_assign_parking(doc)

	return "Confirmed"


def auto_assign_parking(reservation_doc):
	"""Auto-assign parking slots for each row in the reservation's parking_details child table."""
	if not reservation_doc.parking_details:
		return

	member_name = frappe.db.get_value("Member", {"app_user": reservation_doc.app_user}, "name")
	member_location = frappe.db.get_value("Member", member_name, "location") if member_name else None

	for row in reservation_doc.parking_details:
		if row.parking_allocation:
			continue

		if not row.vehicle_type or not row.vehicle_number:
			continue

		slot_filters = {
			"status": "Available",
			"enabled": 1,
			"slot_type": row.vehicle_type,
		}
		if member_location:
			slot_filters["location"] = member_location

		available_slot = frappe.db.get_value(
			"Parking Slot",
			slot_filters,
			["name", "slot_name"],
			as_dict=True,
		)

		if not available_slot:
			frappe.msgprint(
				f"No available {row.vehicle_type} parking slot found for vehicle {row.vehicle_number}. "
				"Supervisor can assign manually later."
			)
			continue

		allocation = frappe.get_doc({
			"doctype": "Parking Allocation",
			"parking_slot": available_slot.name,
			"vehicle_number": row.vehicle_number,
			"member": member_name,
			"app_user": reservation_doc.app_user,
			"allocation_type": "Member",
			"reservation": reservation_doc.name,
			"allocated_to": reservation_doc.booking_to,
		})
		allocation.insert(ignore_permissions=True)

		frappe.db.set_value("Reservation Parking", row.name, {
			"parking_slot": available_slot.name,
			"parking_allocation": allocation.name,
		})

		frappe.msgprint(f"Parking slot {available_slot.slot_name} assigned for vehicle {row.vehicle_number}")


@frappe.whitelist()
def pay_now(reservation_name):
	payment_name = frappe.db.get_value("Reservation", reservation_name, "payment")
	if not payment_name:
		frappe.throw("No payment linked to this reservation")

	frappe.db.set_value("Payment", payment_name, "payment_status", "Paid")
	frappe.db.set_value("Payment", payment_name, "payment_date", frappe.utils.now_datetime())
	frappe.db.set_value("Reservation", reservation_name, "payment_status", "Paid")
	return payment_name


@frappe.whitelist()
def expire_bookings():
	expired = frappe.get_all(
		"Reservation",
		filters={"booking_status": ["in", ["Pending", "Booked"]], "booking_to": ["<", frappe.utils.now()]},
		pluck="name"
	)
	affected_users = set()
	for name in expired:
		space = frappe.db.get_value("Reservation", name, "space")
		app_user = frappe.db.get_value("Reservation", name, "app_user")
		frappe.db.set_value("Reservation", name, "booking_status", "Completed")
		if space:
			frappe.db.set_value("Space", space, "availability_status", "Available")
		release_reservation_parking(name)
		if app_user:
			affected_users.add(app_user)

	for app_user in affected_users:
		member = frappe.db.get_value("Member", {"app_user": app_user}, "name")
		if not member:
			continue
		active_bookings = frappe.db.count("Reservation", {
			"app_user": app_user,
			"booking_status": ["in", ["Booked"]],
		})
		if active_bookings == 0:
			frappe.db.set_value("Member", member, "active", 0)


def release_reservation_parking(reservation_name):
	"""Release all active parking allocations linked to a reservation."""
	allocations = frappe.get_all(
		"Parking Allocation",
		filters={"reservation": reservation_name, "allocation_status": "Active"},
		pluck="name",
	)
	for alloc_name in allocations:
		alloc = frappe.get_doc("Parking Allocation", alloc_name)
		alloc.allocation_status = "Released"
		alloc.allocated_to = now_datetime()
		alloc.save(ignore_permissions=True)
		if alloc.parking_slot:
			frappe.db.set_value("Parking Slot", alloc.parking_slot, "status", "Available")
