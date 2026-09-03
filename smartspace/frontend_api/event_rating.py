import frappe
from frappe.utils import now_datetime, get_datetime, today

from smartspace.frontend_api.auth import get_session_app_user, require_active_member
from smartspace.frontend_api.member import _get_member_locations


@frappe.whitelist()
def get_completed_events(page=1, page_size=10):
	"""Get completed events."""
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	member_locations = _get_member_locations()
	now = now_datetime()

	filters = {"event_status": "Published", "end_date": ["<", now]}
	if member_locations:
		filters["location"] = ["in", member_locations]

	page = int(page)
	page_size = int(page_size)
	start = (page - 1) * page_size

	events = frappe.db.get_list(
		"Space Event",
		filters=filters,
		fields=["name", "event_name", "location", "event_theme",
				"start_date", "end_date", "description"],
		order_by="end_date desc",
		start=start,
		limit=page_size,
	)

	for e in events:
		if e.location:
			e["location_name"] = frappe.db.get_value("Location", e.location, "location_name") or e.location

		existing = frappe.db.get_value(
			"Event Rating",
			{"event": e.name, "app_user": app_user},
			["name", "rating", "review", "rating_date"],
			as_dict=True,
		)
		if existing:
			e["my_rating"] = existing.rating
			e["my_review"] = existing.review
			e["my_rating_date"] = existing.rating_date
			e["has_rated"] = True
		else:
			e["has_rated"] = False

		avg = frappe.db.get_all(
			"Event Rating",
			filters={"event": e.name},
			fields=["rating"],
		)
		if avg:
			e["avg_rating"] = round(sum(r.rating for r in avg) / len(avg), 1)
			e["rating_count"] = len(avg)
		else:
			e["avg_rating"] = 0
			e["rating_count"] = 0

	total = frappe.db.count("Space Event", filters)

	return {
		"events": events,
		"total": total,
		"page": page,
		"page_size": page_size,
		"total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
	}


@frappe.whitelist()
def submit_event_rating(event, rating, review=None):
	"""Submit event rating."""
	require_active_member()
	app_user = get_session_app_user()
	if not app_user:
		frappe.throw("No App User found for current session user")

	rating = float(rating)
	if rating < 0.5 or rating > 5:
		frappe.throw("Rating must be between 0.5 and 5")

	if not frappe.db.exists("Space Event", event):
		frappe.throw("Event not found")

	end_date = frappe.db.get_value("Space Event", event, "end_date")
	if end_date and get_datetime(end_date) > get_datetime(now_datetime()):
		frappe.throw("You can only rate events that have ended")

	existing = frappe.db.get_value(
		"Event Rating",
		{"event": event, "app_user": app_user},
		"name",
	)

	if existing:
		doc = frappe.get_doc("Event Rating", existing)
		doc.rating = rating
		if review is not None:
			doc.review = review
		doc.rating_date = today()
		doc.save(ignore_permissions=True)
		action = "updated"
	else:
		doc = frappe.get_doc({
			"doctype": "Event Rating",
			"event": event,
			"app_user": app_user,
			"rating": rating,
			"review": review,
			"rating_date": today(),
		})
		doc.insert(ignore_permissions=True)
		action = "submitted"

	return {
		"success": True,
		"message": f"Rating {action} successfully",
		"rating": doc.rating,
		"review": doc.review,
	}


@frappe.whitelist()
def get_event_ratings_summary(event=None, from_date=None, to_date=None, location=None):
	"""Get rating summaries."""
	from smartspace.frontend_api.analytics import _check_admin_role
	_check_admin_role()

	if event:
		ratings = frappe.db.get_all(
			"Event Rating",
			filters={"event": event},
			fields=["name", "app_user", "rating", "review", "rating_date"],
			order_by="rating_date desc",
		)
		for r in ratings:
			au = frappe.db.get_value("App User", r.app_user, ["full_name", "role"], as_dict=True)
			if au:
				r["user_name"] = au.full_name
				r["user_role"] = au.role
			else:
				r["user_name"] = "Unknown"
				r["user_role"] = "-"

		event_name = frappe.db.get_value("Space Event", event, "event_name")
		avg = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else 0

		return {
			"event": event,
			"event_name": event_name,
			"total_ratings": len(ratings),
			"avg_rating": avg,
			"ratings": ratings,
		}

	filters = {}
	if from_date:
		filters["rating_date"] = [">=", from_date]
	if to_date:
		if "rating_date" in filters:
			filters["rating_date"] = ["between", [from_date, to_date]]
		else:
			filters["rating_date"] = ["<=", to_date]

	all_ratings = frappe.db.get_all(
		"Event Rating",
		filters=filters,
		fields=["name", "event", "app_user", "rating", "review", "rating_date"],
	)

	if location:
		event_names = set()
		space_events = frappe.get_all("Space Event", {"location": location}, ["name"])
		for se in space_events:
			event_names.add(se.name)
		all_ratings = [r for r in all_ratings if r.event in event_names]

	event_map = {}
	for r in all_ratings:
		if r.event not in event_map:
			event_name = frappe.db.get_value("Space Event", r.event, "event_name")
			event_map[r.event] = {
				"event": r.event,
				"event_name": event_name,
				"ratings": [],
				"total": 0,
				"sum": 0,
			}
		event_map[r.event]["ratings"].append(r)
		event_map[r.event]["total"] += 1
		event_map[r.event]["sum"] += r.rating

	events_list = []
	for ev_name, data in event_map.items():
		events_list.append({
			"event": ev_name,
			"event_name": data["event_name"],
			"total_ratings": data["total"],
			"avg_rating": round(data["sum"] / data["total"], 1) if data["total"] else 0,
		})
	events_list.sort(key=lambda x: x["avg_rating"], reverse=True)

	total_ratings = len(all_ratings)
	avg_rating = round(sum(r.rating for r in all_ratings) / total_ratings, 1) if total_ratings else 0
	rated_events = len(event_map)

	distribution = {0.5: 0, 1: 0, 1.5: 0, 2: 0, 2.5: 0, 3: 0, 3.5: 0, 4: 0, 4.5: 0, 5: 0}
	for r in all_ratings:
		key = r.rating
		if key in distribution:
			distribution[key] += 1

	return {
		"total_ratings": total_ratings,
		"rated_events": rated_events,
		"avg_rating": avg_rating,
		"events": events_list,
		"distribution": distribution,
	}
