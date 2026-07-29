# Copyright (c) 2026, avishna and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr
from frappe.share import add as add_share


class AppUser(Document):
	def validate(self):
		self.set_full_name()
		self.validate_email()

	def before_save(self):
		self.set_full_name()

	def after_insert(self):
		self.create_frappe_user()
		self.share_with_user()

	def on_update(self):
		self.sync_frappe_user()
		self.share_with_user()

	def on_trash(self):
		self.handle_user_deletion()

	def set_full_name(self):
		"""Generate full_name from first_name and last_name"""
		self.full_name = " ".join(filter(None, [cstr(self.first_name).strip(), cstr(self.last_name).strip()]))

	def validate_email(self):
		"""Validate email format"""
		if self.email:
			self.email = self.email.strip().lower()
			if not frappe.utils.validate_email_address(self.email):
				frappe.throw(_("Invalid email address: {0}").format(self.email))
	
	def create_frappe_user(self):
		"""Create a corresponding Frappe User when App User is created"""
		if self.user:
			return

		if frappe.db.exists("User", self.email):
			existing_user = frappe.get_doc("User", self.email)
			self.db_set("user", existing_user.name, update_modified=False)
			self.sync_frappe_user()
			return

		try:
			user = frappe.new_doc("User")
			user.email = self.email
			user.first_name = self.first_name
			user.last_name = self.last_name or ""
			user.full_name = self.full_name
			user.enabled = self.active
			user.new_password = self.get_password("password")
			user.send_welcome_email = 0

			if self.role:
				user.append("roles", {"role": self.role})

			user.flags.ignore_permissions = True
			user.flags.no_welcome_mail = True
			user.insert()

			self.db_set("user", user.name, update_modified=False)
			frappe.msgprint(_("User {0} created successfully").format(self.email), indicator="green", alert=True)

		except Exception as e:
			frappe.log_error(f"Error creating user for App User {self.name}: {str(e)}")
			frappe.throw(_("Error creating user: {0}").format(str(e)))

	def sync_frappe_user(self):
		"""Sync App User changes to linked Frappe User"""
		if not self.user:
			return

		if not frappe.db.exists("User", self.user):
			return

		try:
			user = frappe.get_doc("User", self.user)
			updated = False

			if user.first_name != self.first_name:
				user.first_name = self.first_name
				updated = True

			if user.last_name != (self.last_name or ""):
				user.last_name = self.last_name or ""
				updated = True

			if user.full_name != self.full_name:
				user.full_name = self.full_name
				updated = True

			if user.enabled != self.active:
				user.enabled = self.active
				updated = True

			if self.has_value_changed("role"):
				user.roles = []
				if self.role:
					user.append("roles", {"role": self.role})
				updated = True

			if self.has_value_changed("password"):
				password = self.get_password("password")
				if password:
					user.new_password = password
					updated = True

			if self.has_value_changed("email") and self.email != user.email:
				if frappe.db.exists("User", self.email):
					frappe.throw(_("User with email {0} already exists").format(self.email))
				user.email = self.email
				updated = True

			if updated:
				user.flags.ignore_permissions = True
				user.save()

		except Exception as e:
			frappe.log_error(f"Error syncing user for App User {self.name}: {str(e)}")
			frappe.throw(_("Error syncing user: {0}").format(str(e)))
			
	def handle_user_deletion(self):
		if not self.user:
			return
		if not frappe.db.exists("User", self.user):
			return
		try:
			frappe.delete_doc(
				"User",
				self.user,
				ignore_permissions=True
			)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Error deleting User {self.user}"
			)

	def share_with_user(self):
		"""Share this App User document with the linked Frappe User"""
		if not self.user:
			return
		if not frappe.db.exists("DocShare", {"share_doctype": self.doctype, "share_name": self.name, "user": self.user}):
			add_share(self.doctype, self.name, self.user, read=1, write=1)
