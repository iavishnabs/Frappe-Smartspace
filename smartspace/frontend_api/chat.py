import frappe
from frappe.utils import now_datetime

from smartspace.frontend_api.auth import get_session_app_user, is_session_user_admin


def _get_admin_app_user():
	"""Return the first App Admin App User name (shared admin inbox)."""
	return frappe.db.get_value("App User", {"role": "App Admin"}, "name")


@frappe.whitelist()
def send_message(message, related_doctype=None, related_name=None):
	"""Send a chat message from the current user to the admin inbox."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	if not message or not message.strip():
		frappe.throw("Message cannot be empty")

	admin_user = _get_admin_app_user()
	if not admin_user:
		frappe.throw("No admin user found in the system")

	doc = frappe.get_doc({
		"doctype": "Chat",
		"sender": app_user,
		"receiver": admin_user,
		"message": message.strip(),
		"message_date": now_datetime(),
		"is_admin_reply": 0,
	})
	if related_doctype:
		doc.related_doctype = related_doctype
	if related_name:
		doc.related_name = related_name
	doc.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Message sent",
		"chat_name": doc.name,
		"message_date": doc.message_date,
	}


@frappe.whitelist()
def get_chat_history(limit=50):
	"""Get chat history between the current user and admin."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	admin_user = _get_admin_app_user()

	messages = frappe.get_all(
		"Chat",
		filters=[
			["Chat", "sender", "in", [app_user, admin_user]],
			["Chat", "receiver", "in", [app_user, admin_user]],
		],
		fields=["name", "sender", "receiver", "message", "message_date",
				"is_admin_reply", "is_read", "related_doctype", "related_name"],
		order_by="message_date asc",
		limit=int(limit),
	)

	for m in messages:
		if m.sender == admin_user:
			m["is_admin"] = True
		else:
			m["is_admin"] = False

	return {"messages": messages}


@frappe.whitelist()
def admin_send_message(receiver, message):
	"""Admin replies to a specific user."""
	if not is_session_user_admin():
		frappe.throw("Only admins can send admin replies")

	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	if not message or not message.strip():
		frappe.throw("Message cannot be empty")

	if not frappe.db.exists("App User", receiver):
		frappe.throw("Receiver not found")

	doc = frappe.get_doc({
		"doctype": "Chat",
		"sender": app_user,
		"receiver": receiver,
		"message": message.strip(),
		"message_date": now_datetime(),
		"is_admin_reply": 1,
	})
	doc.insert(ignore_permissions=True)

	return {
		"success": True,
		"message": "Reply sent",
		"chat_name": doc.name,
		"message_date": doc.message_date,
	}


@frappe.whitelist()
def get_admin_chat_list():
	"""Get list of users who have chatted with admin, with latest message and unread count."""
	if not is_session_user_admin():
		frappe.throw("Only admins can view chat list")

	admin_user = _get_admin_app_user()

	all_chats = frappe.get_all(
		"Chat",
		filters=[
			["Chat", "sender", "in", [admin_user]],
			["Chat", "receiver", "in", [admin_user]],
		],
		fields=["name", "sender", "receiver", "message", "message_date",
				"is_admin_reply", "is_read"],
		order_by="message_date desc",
	)

	user_map = {}
	for c in all_chats:
		other_user = c.receiver if c.sender == admin_user else c.sender
		if other_user not in user_map:
			user_map[other_user] = {
				"app_user": other_user,
				"last_message": c.message,
				"last_message_date": c.message_date,
				"unread_count": 0,
				"is_admin_reply": c.is_admin_reply,
			}
			if not c.is_admin_reply and not c.is_read:
				user_map[other_user]["unread_count"] = 1
		else:
			if not c.is_admin_reply and not c.is_read:
				user_map[other_user]["unread_count"] += 1

	users = list(user_map.values())
	for u in users:
		au = frappe.db.get_value("App User", u["app_user"], ["full_name", "role"], as_dict=True)
		if au:
			u["user_name"] = au.full_name
			u["user_role"] = au.role
		else:
			u["user_name"] = "Unknown"
			u["user_role"] = "-"

	users.sort(key=lambda x: x["last_message_date"], reverse=True)

	return {"chats": users}


@frappe.whitelist()
def get_admin_conversation(user_app):
	"""Get full conversation between admin and a specific user."""
	if not is_session_user_admin():
		frappe.throw("Only admins can view conversations")

	admin_user = _get_admin_app_user()

	messages = frappe.get_all(
		"Chat",
		filters=[
			["Chat", "sender", "in", [admin_user, user_app]],
			["Chat", "receiver", "in", [admin_user, user_app]],
		],
		fields=["name", "sender", "receiver", "message", "message_date",
				"is_admin_reply", "is_read", "related_doctype", "related_name"],
		order_by="message_date asc",
	)

	for m in messages:
		m["is_admin"] = m.sender == admin_user

	unread = [m for m in messages if not m.is_admin_reply and not m.is_read]
	for m in unread:
		frappe.db.set_value("Chat", m.name, "is_read", 1, update_modified=False)

	user_info = frappe.db.get_value("App User", user_app, ["full_name", "role"], as_dict=True)

	return {
		"messages": messages,
		"user_name": user_info.full_name if user_info else "Unknown",
		"user_role": user_info.role if user_info else "-",
	}


@frappe.whitelist()
def get_unread_count():
	"""Get unread message count for the current user (from admin)."""
	app_user = get_session_app_user()
	if not app_user:
		return {"unread_count": 0}

	admin_user = _get_admin_app_user()
	count = frappe.db.count("Chat", {
		"sender": admin_user,
		"receiver": app_user,
		"is_admin_reply": 1,
		"is_read": 0,
	})

	return {"unread_count": count}
