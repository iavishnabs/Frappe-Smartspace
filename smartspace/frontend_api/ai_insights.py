import frappe
import re
from frappe.utils import getdate, nowdate, add_months, add_days, cint
from collections import Counter, OrderedDict
from .analytics import (
    get_analytics_overview, get_location_wise_stats,
    get_revenue_trend, get_booking_trend,
    get_space_type_distribution, get_asset_status_distribution,
    get_events_list, get_recent_bookings, get_all_locations,
)


def _check_admin_role():
	"""Raise error if current user doesn't have App Admin or Administrator role."""
	roles = frappe.get_roles(frappe.session.user)
	if "App Admin" not in roles and "Administrator" not in roles:
		frappe.throw("You don't have permission to access this resource.", frappe.PermissionError)


@frappe.whitelist()
def get_insights_summary(from_date=None, to_date=None, location=None):
    """Generate plain-text AI insights from analytics data."""
    _check_admin_role()
    overview = get_analytics_overview(from_date, to_date, location)
    loc_stats = get_location_wise_stats(from_date, to_date)
    revenue_trend = get_revenue_trend(from_date, to_date, location)
    booking_trend = get_booking_trend(from_date, to_date, location)
    space_dist = get_space_type_distribution(location)
    asset_dist = get_asset_status_distribution(location)

    insights = []

    # ── Revenue insights ──
    rev_values = revenue_trend.get("values", [])
    rev_labels = revenue_trend.get("labels", [])
    if len(rev_values) >= 2:
        prev_rev = rev_values[-2]
        curr_rev = rev_values[-1]
        diff = curr_rev - prev_rev
        if prev_rev > 0:
            change = (diff / prev_rev) * 100
            if abs(change) > 500:
                insights.append(
                    f"Revenue went from ₹{prev_rev:,.0f} to ₹{curr_rev:,.0f} in {rev_labels[-1]} "
                    f"(up by ₹{abs(diff):,.0f}) — significant growth from a small base."
                )
            else:
                direction = "increased" if diff > 0 else "decreased"
                insights.append(
                    f"Revenue {direction} by {abs(change):.0f}% in {rev_labels[-1]} "
                    f"compared to {rev_labels[-2]} (₹{prev_rev:,.0f} → ₹{curr_rev:,.0f})."
                )
        else:
            insights.append(
                f"Revenue in {rev_labels[-1]} is ₹{curr_rev:,.0f} "
                f"(previous month had ₹0 revenue)."
            )
    elif len(rev_values) == 1:
        insights.append(f"Revenue for {rev_labels[0]} is ₹{rev_values[0]:,.0f}.")

    # ── Booking insights ──
    bk_totals = booking_trend.get("totals", [])
    bk_labels = booking_trend.get("labels", [])
    if len(bk_totals) >= 2:
        prev_bk = bk_totals[-2]
        curr_bk = bk_totals[-1]
        if prev_bk > 0:
            change = ((curr_bk - prev_bk) / prev_bk) * 100
            if abs(change) > 500:
                insights.append(
                    f"Bookings went from {prev_bk} to {curr_bk} in {bk_labels[-1]} "
                    f"— significant growth from a small base."
                )
            else:
                direction = "up" if curr_bk > prev_bk else "down"
                insights.append(
                    f"Bookings are {direction} {abs(change):.0f}% in {bk_labels[-1]} "
                    f"({curr_bk} vs {prev_bk} previous period)."
                )
        else:
            insights.append(
                f"Bookings in {bk_labels[-1]}: {curr_bk} (previous month had 0 bookings)."
            )

    # ── Space type insights ──
    space_labels = space_dist.get("labels", [])
    space_values = space_dist.get("values", [])
    if space_labels and space_values:
        top_idx = space_values.index(max(space_values))
        total_spaces = sum(space_values)
        pct = (space_values[top_idx] / total_spaces * 100) if total_spaces else 0
        insights.append(
            f"{space_labels[top_idx]} is the most common space type, "
            f"accounting for {pct:.0f}% of all spaces ({space_values[top_idx]} out of {total_spaces})."
        )

    # ── Asset insights ──
    asset_labels = asset_dist.get("labels", [])
    asset_values = asset_dist.get("values", [])
    if asset_labels and asset_values:
        total_assets = sum(asset_values)
        for i, label in enumerate(asset_labels):
            pct = (asset_values[i] / total_assets * 100) if total_assets else 0
            if label == "Allocated" and pct > 70:
                insights.append(
                    f"{pct:.0f}% of assets are allocated — consider acquiring more assets to meet demand."
                )
            elif label == "Available" and pct > 50:
                insights.append(
                    f"{pct:.0f}% of assets are available — utilization is low, consider reallocating."
                )

    # ── Location performance ──
    locations = loc_stats.get("locations", [])
    if len(locations) > 1:
        top_loc = max(locations, key=lambda x: x.get("revenue", 0))
        low_loc = min(locations, key=lambda x: x.get("revenue", 0))
        insights.append(
            f"{top_loc['location_name']} is the top-performing location by revenue "
            f"(₹{top_loc['revenue']:,.0f}), while {low_loc['location_name']} "
            f"has the lowest revenue (₹{low_loc['revenue']:,.0f})."
        )

    # ── Event insights ──
    events = get_events_list(from_date, to_date, location).get("events", [])
    if events:
        completed = [e for e in events if e.get("event_status") == "Completed"]
        total_collected = sum(e.get("total_collected", 0) for e in events)
        total_spent = sum(e.get("total_spent", 0) for e in events)
        insights.append(
            f"{len(events)} events were organized, with {len(completed)} completed. "
            f"Total collected: ₹{total_collected:,.0f}, total spent: ₹{total_spent:,.0f}."
        )
    else:
        insights.append("No events were organized in this period — consider planning community events.")

    # ── Member insights ──
    total_members = overview.get("total_members", 0)
    active_members = overview.get("active_members", 0)
    if total_members > 0:
        active_pct = (active_members / total_members * 100) if total_members else 0
        insights.append(
            f"{active_members} out of {total_members} members are active "
            f"({active_pct:.0f}% engagement rate)."
        )

    return {"insights": insights}


@frappe.whitelist()
def ask_question(question, from_date=None, to_date=None, location=None):
    """Natural language Q&A — answer admin questions based on analytics data."""
    _check_admin_role()
    if not question or not question.strip():
        return {"answer": "Please ask a question."}

    q = question.lower().strip()

    # Gather all data once
    overview = get_analytics_overview(from_date, to_date, location)
    loc_stats = get_location_wise_stats(from_date, to_date)
    locations = loc_stats.get("locations", [])
    revenue_trend = get_revenue_trend(from_date, to_date, location)
    booking_trend = get_booking_trend(from_date, to_date, location)
    space_dist = get_space_type_distribution(location)
    asset_dist = get_asset_status_distribution(location)
    events = get_events_list(from_date, to_date, location).get("events", [])
    bookings = get_recent_bookings(from_date, to_date, location, limit=200).get("bookings", [])

    # ── Intent scoring: detect which topics the question is about ──
    topic_keywords = {
        "profit": ["profit", "loss", "margin", "net", "surplus", "deficit", "bottom line", "earnings after"],
        "revenue": ["revenue", "income", "earning", "money", "financial", "payment", "paid", "rupees", "rs", "top line", "turnover"],
        "expense": ["expense", "cost", "spend", "spent", "expenditure", "vendor cost", "purchase cost", "event cost", "operating cost"],
        "booking": ["booking", "reservation", "book", "reserve", "slot", "appointment"],
        "location": ["location", "branch", "office", "place", "where", "which location", "best location", "top location", "perform"],
        "asset": ["asset", "equipment", "inventory", "laptop", "chair", "desk", "furniture", "device"],
        "event": ["event", "gather", "meetup", "party", "celebration", "function", "theme", "community"],
        "member": ["member", "user", "customer", "people", "client", "engagement", "active"],
        "vendor": ["vendor", "supplier", "purchase", "procurement"],
        "space": ["space", "room", "cabin", "conference", "private office", "workspace", "coworking"],
        "growth": ["growth", "trend", "trending", "decline", "rising", "falling", "compare", "change", "progress", "month over month", "mom", "yoy", "year over year"],
        "suggestion": ["suggest", "recommend", "recommendation", "advice", "how can", "how to", "what should", "improve", "increase", "boost", "strategy", "tips", "ways", "ideas", "should we", "organize", "plan", "what to do", "what can", "help us", "grow", "optimize", "better"],
        "overview": ["overview", "summary", "report", "status", "overall", "dashboard", "everything", "all", "general", "brief"],
    }

    scores = {}
    for topic, keywords in topic_keywords.items():
        score = 0
        for kw in keywords:
            if kw in q:
                score += len(kw.split())  # multi-word keywords get higher weight
        if score > 0:
            scores[topic] = score

    # If no topic matched, check for generic question words
    generic_words = ["details", "share", "show", "tell", "about", "what", "how", "give", "get", "see", "view", "info", "information", "data"]
    if not scores:
        if any(w in q for w in generic_words):
            scores["overview"] = 1
        else:
            return {
                "answer": (
                    "I'm not sure what you're asking about. I can help with:\n"
                    "• Revenue, profit, and expenses\n"
                    "• Bookings and reservations\n"
                    "• Location performance\n"
                    "• Assets and inventory\n"
                    "• Events and themes\n"
                    "• Members and engagement\n"
                    "• Vendors and purchases\n"
                    "• Spaces and utilization\n"
                    "• Growth trends\n"
                    "• Suggestions to improve\n\n"
                    "Try: \"Share profit details\" or \"Which location performs best?\""
                )
            }

    # Sort topics by score (highest first)
    sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # If suggestion intent is detected, combine with ALL other matched topics
    # Otherwise, include all topics with score > 0
    is_suggestion = "suggestion" in scores

    if is_suggestion:
        top_topics = [t[0] for t in sorted_topics if t[0] != "suggestion"]
        # If no other topic matched alongside suggestion, use suggestion alone
        if not top_topics:
            top_topics = ["overview"]
    else:
        # Include all topics that scored, but filter out "overview" if other specific topics matched
        top_topics = [t[0] for t in sorted_topics]
        if len(top_topics) > 1 and "overview" in top_topics:
            top_topics.remove("overview")

    # ── Build answer based on detected topics ──
    answer_parts = []

    # ── Profit ──
    if "profit" in top_topics:
        total_revenue = overview.get("total_revenue", 0)
        vendor_spend = overview.get("vendor_total_spend", 0)
        event_spend = sum(e.get("total_spent", 0) for e in events)
        total_expenses = vendor_spend + event_spend
        profit = total_revenue - total_expenses
        margin = (profit / total_revenue * 100) if total_revenue > 0 else 0

        if is_suggestion:
            parts = [f"Current profit: ₹{profit:,.0f} (margin: {margin:.0f}%)."]
            if total_revenue > 0 and total_expenses > 0:
                if profit < 0:
                    parts.append(f"You're operating at a loss. Expenses (₹{total_expenses:,.0f}) exceed revenue (₹{total_revenue:,.0f}). Urgently reduce costs or increase revenue.")
                elif margin < 20:
                    parts.append(f"Margin is low at {margin:.0f}%. Focus on increasing revenue or reducing expenses.")
                elif margin > 50:
                    parts.append(f"Healthy margin of {margin:.0f}%. Maintain current pricing and cost structure.")
                else:
                    parts.append(f"Margin is {margin:.0f}% — there's room to optimize either pricing or costs.")
            if vendor_spend > 0 and vendor_spend > total_revenue * 0.3:
                parts.append(f"Vendor expenses (₹{vendor_spend:,.0f}) are {vendor_spend/total_revenue*100:.0f}% of revenue — consider negotiating better rates.")
            if event_spend > 0 and event_spend > total_revenue * 0.2:
                parts.append(f"Event expenses (₹{event_spend:,.0f}) are high relative to revenue — ensure events generate enough collection.")
            if not parts[1:]:
                parts.append("To improve profit: increase booking volume, optimize pricing, negotiate vendor costs, and ensure events are revenue-generating.")
            answer_parts.append("Profit Strategy: " + " ".join(parts))
        else:
            parts = [
                f"Here's your profit breakdown:",
                f"\n  • Total Revenue: ₹{total_revenue:,.0f}",
                f"\n  • Vendor Expenses: ₹{vendor_spend:,.0f}",
                f"\n  • Event Expenses: ₹{event_spend:,.0f}",
                f"\n  • Total Expenses: ₹{total_expenses:,.0f}",
                f"\n  • Net Profit: ₹{profit:,.0f}",
            ]
            if total_revenue > 0:
                parts.append(f"\n  • Profit Margin: {margin:.0f}%")
            if profit > 0:
                parts.append(f"\n\nYou're operating at a profit of ₹{profit:,.0f}.")
            elif profit < 0:
                parts.append(f"\n\nYou're operating at a loss of ₹{abs(profit):,.0f}. Expenses exceed revenue.")
            else:
                parts.append(f"\n\nRevenue and expenses break even.")
            answer_parts.append("".join(parts))

    # ── Expense ──
    if "expense" in top_topics:
        vendor_spend = overview.get("vendor_total_spend", 0)
        event_spend = sum(e.get("total_spent", 0) for e in events)
        total_expenses = vendor_spend + event_spend
        total_revenue = overview.get("total_revenue", 0)

        if is_suggestion:
            parts = [f"Total expenses: ₹{total_expenses:,.0f} (Vendor: ₹{vendor_spend:,.0f}, Events: ₹{event_spend:,.0f})."]
            if vendor_spend > 0 and total_revenue > 0:
                vendor_pct = vendor_spend / total_revenue * 100
                if vendor_pct > 30:
                    parts.append(f"Vendor costs are {vendor_pct:.0f}% of revenue — look for cheaper suppliers or bulk purchase discounts.")
            if event_spend > 0 and total_revenue > 0:
                event_pct = event_spend / total_revenue * 100
                if event_pct > 20:
                    parts.append(f"Event costs are {event_pct:.0f}% of revenue — ensure events generate enough collection to justify spending.")
            if not parts[1:]:
                parts.append("To reduce expenses: negotiate vendor rates, bulk purchase assets, and track event ROI.")
            answer_parts.append("Expense Strategy: " + " ".join(parts))
        else:
            parts = [
                f"Expense breakdown:",
                f"\n  • Vendor/Purchase spend: ₹{vendor_spend:,.0f}",
                f"\n  • Event spend: ₹{event_spend:,.0f}",
                f"\n  • Total expenses: ₹{total_expenses:,.0f}",
            ]
            if total_revenue > 0:
                parts.append(f"\n  • Expenses are {total_expenses/total_revenue*100:.0f}% of revenue.")
            answer_parts.append("".join(parts))

    # ── Revenue ──
    if "revenue" in top_topics:
        total = overview.get("total_revenue", 0)
        rev_values = revenue_trend.get("values", [])
        rev_labels = revenue_trend.get("labels", [])

        if is_suggestion:
            answer_parts.append(_revenue_suggestions(overview, locations, revenue_trend, events, bookings))
        else:
            parts = [f"Total revenue is ₹{total:,.0f}."]
            if len(rev_values) >= 2:
                prev_rev = rev_values[-2]
                curr_rev = rev_values[-1]
                diff = curr_rev - prev_rev
                if prev_rev > 0:
                    change = (diff / prev_rev * 100)
                    if abs(change) > 500:
                        parts.append(f"Revenue went from ₹{prev_rev:,.0f} to ₹{curr_rev:,.0f} (up by ₹{abs(diff):,.0f}) — significant growth from a small base.")
                    else:
                        direction = "up" if diff > 0 else "down"
                        parts.append(f"It's {direction} {abs(change):.0f}% compared to last month (₹{prev_rev:,.0f} → ₹{curr_rev:,.0f}).")
                else:
                    parts.append(f"Previous month had ₹0 revenue, current month is ₹{curr_rev:,.0f}.")
            if locations:
                top = max(locations, key=lambda x: x.get("revenue", 0))
                low = min(locations, key=lambda x: x.get("revenue", 0))
                parts.append(f"Top location: {top['location_name']} (₹{top['revenue']:,.0f})")
                if low.get("revenue", 0) == 0 and low["location_name"] != top["location_name"]:
                    parts.append(f"Lowest: {low['location_name']} (₹0 — no revenue yet).")
            answer_parts.append(" ".join(parts))

    # ── Booking ──
    if "booking" in top_topics:
        total = overview.get("total_bookings", 0)
        pending = overview.get("pending_bookings", 0)
        completed = overview.get("completed_bookings", 0)
        cancelled = overview.get("cancelled_bookings", 0)

        if is_suggestion:
            answer_parts.append(_booking_suggestions(overview, booking_trend, bookings))
        else:
            parts = [f"Total bookings: {total} (Completed: {completed}, Pending: {pending}, Cancelled: {cancelled})."]
            bk_totals = booking_trend.get("totals", [])
            if len(bk_totals) >= 2:
                prev_bk = bk_totals[-2]
                curr_bk = bk_totals[-1]
                if prev_bk > 0:
                    change = ((curr_bk - prev_bk) / prev_bk * 100)
                    if abs(change) > 500:
                        parts.append(f"Bookings went from {prev_bk} to {curr_bk} — significant growth from a small base.")
                    else:
                        direction = "up" if curr_bk > prev_bk else "down"
                        parts.append(f"Trend: {direction} {abs(change):.0f}% month-over-month ({prev_bk} → {curr_bk}).")
                else:
                    parts.append(f"Previous month had 0 bookings, current month has {curr_bk}.")
            answer_parts.append(" ".join(parts))

    # ── Location ──
    if "location" in top_topics:
        if not locations:
            answer_parts.append("No location data available for this period.")
        elif is_suggestion:
            answer_parts.append(_location_suggestions(locations))
        else:
            sorted_locs = sorted(locations, key=lambda x: x.get("revenue", 0), reverse=True)
            parts = ["Location performance (by revenue):"]
            for loc in sorted_locs[:5]:
                parts.append(
                    f"{loc['location_name']}: ₹{loc['revenue']:,.0f} revenue, "
                    f"{loc['total_bookings']} bookings, {loc['total_spaces']} spaces, "
                    f"{loc['total_members']} members."
                )
            answer_parts.append(" ".join(parts))

    # ── Asset ──
    if "asset" in top_topics:
        total = overview.get("total_assets", 0)
        allocated = overview.get("allocated_assets", 0)
        available = overview.get("available_assets", 0)
        maintenance = overview.get("maintenance_assets", 0)
        damaged = overview.get("damaged_assets", 0)
        cost = overview.get("asset_purchase_cost", 0)

        if is_suggestion:
            parts = []
            if total > 0:
                alloc_pct = (allocated / total * 100) if total else 0
                avail_pct = (available / total * 100) if total else 0
                if alloc_pct > 70:
                    parts.append(f"{alloc_pct:.0f}% of assets are allocated — consider acquiring more to meet demand.")
                if avail_pct > 50:
                    parts.append(f"{avail_pct:.0f}% of assets are available — utilization is low, consider reallocating.")
                if damaged > 0:
                    parts.append(f"{damaged} damaged assets need repair or replacement.")
                if maintenance > 0:
                    parts.append(f"{maintenance} assets are under maintenance.")
                if not parts:
                    parts.append(f"Asset allocation looks balanced: {allocated} allocated, {available} available out of {total} total.")
            else:
                parts.append("No assets found in the system.")
            answer_parts.append(" ".join(parts))
        else:
            answer_parts.append(
                f"Total assets: {total} (Allocated: {allocated}, Available: {available}, "
                f"Maintenance: {maintenance}, Damaged: {damaged}). "
                f"Total purchase cost: ₹{cost:,.0f}."
            )

    # ── Event ──
    if "event" in top_topics:
        if is_suggestion:
            answer_parts.append(_event_suggestions_text(overview, events, locations, bookings, space_dist))
        elif not events:
            answer_parts.append("No events were organized in this period. Consider planning community events to boost engagement.")
        else:
            completed = [e for e in events if e.get("event_status") == "Completed"]
            total_collected = sum(e.get("total_collected", 0) for e in events)
            total_spent = sum(e.get("total_spent", 0) for e in events)
            themes = Counter(e.get("event_theme") for e in events if e.get("event_theme"))
            theme_str = ", ".join(f"'{t}' ({c}x)" for t, c in themes.most_common(3))
            parts = [
                f"{len(events)} events organized ({len(completed)} completed).",
                f"Total collected: ₹{total_collected:,.0f}, spent: ₹{total_spent:,.0f}.",
            ]
            if themes:
                parts.append(f"Themes used: {theme_str}.")
            answer_parts.append(" ".join(parts))

    # ── Member ──
    if "member" in top_topics:
        total = overview.get("total_members", 0)
        active = overview.get("active_members", 0)
        pct = (active / total * 100) if total else 0

        if is_suggestion:
            parts = []
            if total == 0:
                parts.append("No members yet — focus on marketing and onboarding to attract members.")
            elif pct < 50:
                parts.append(f"Only {pct:.0f}% of {total} members are active. Consider engagement events or outreach to inactive members.")
            else:
                parts.append(f"{active} out of {total} members are active ({pct:.0f}% engagement) — good engagement rate.")
            answer_parts.append(" ".join(parts))
        else:
            answer_parts.append(f"{total} members in this period, {active} active ({pct:.0f}% engagement).")

    # ── Vendor ──
    if "vendor" in top_topics:
        count = overview.get("vendor_count", 0)
        spend = overview.get("vendor_total_spend", 0)
        if is_suggestion:
            parts = []
            if count == 0:
                parts.append("No vendors registered yet. Add vendors to track procurement and asset purchases.")
            elif spend > 0:
                parts.append(f"{count} vendors with ₹{spend:,.0f} total spend. Review vendor performance to optimize costs.")
            else:
                parts.append(f"{count} vendors registered but no purchases recorded in this period.")
            answer_parts.append(" ".join(parts))
        else:
            answer_parts.append(f"{count} vendors with total spend of ₹{spend:,.0f} in this period.")

    # ── Space ──
    if "space" in top_topics:
        labels = space_dist.get("labels", [])
        values = space_dist.get("values", [])
        if not labels:
            answer_parts.append("No space data available.")
        elif is_suggestion:
            answer_parts.append(_space_suggestions_text(labels, values, bookings))
        else:
            parts = ["Space distribution:"]
            for i, label in enumerate(labels):
                parts.append(f"{label}: {values[i]}")
            answer_parts.append(" ".join(parts))

    # ── Growth (can combine with other topics) ──
    if "growth" in top_topics and not is_suggestion:
        parts = []
        rev_values = revenue_trend.get("values", [])
        bk_totals = booking_trend.get("totals", [])
        if len(rev_values) >= 2:
            rev_diff = rev_values[-1] - rev_values[-2]
            parts.append(f"Revenue: ₹{rev_values[-2]:,.0f} → ₹{rev_values[-1]:,.0f} ({'up' if rev_diff > 0 else 'down'} by ₹{abs(rev_diff):,.0f}).")
        if len(bk_totals) >= 2:
            bk_diff = bk_totals[-1] - bk_totals[-2]
            parts.append(f"Bookings: {bk_totals[-2]} → {bk_totals[-1]} ({'up' if bk_diff > 0 else 'down'} by {abs(bk_diff)}).")
        if parts:
            answer_parts.append("Growth trends: " + " ".join(parts))

    # ── Overview (only if it's the sole topic or explicitly requested) ──
    if "overview" in top_topics and len(top_topics) == 1:
        answer_parts.append(
            f"Overview: Revenue ₹{overview.get('total_revenue', 0):,.0f}, "
            f"{overview.get('total_bookings', 0)} bookings, "
            f"{overview.get('total_assets', 0)} assets, "
            f"{overview.get('total_events', 0)} events, "
            f"{overview.get('total_members', 0)} members, "
            f"{overview.get('vendor_count', 0)} vendors."
        )

    return {"answer": "\n\n".join(answer_parts) if answer_parts else "I couldn't understand your question. Try asking about revenue, bookings, locations, assets, events, members, or spaces."}


def _format_change(curr, prev, unit="₹"):
    """Format a period-over-period change smartly."""
    if prev == 0:
        return f"from {unit}{prev:,.0f} to {unit}{curr:,.0f}"
    diff = curr - prev
    change = (diff / prev * 100)
    if abs(change) > 500:
        return f"from {unit}{prev:,.0f} to {unit}{curr:,.0f} (up by {unit}{abs(diff):,.0f})"
    direction = "up" if diff > 0 else "down"
    return f"{direction} {abs(change):.0f}% ({unit}{prev:,.0f} → {unit}{curr:,.0f})"


def _revenue_suggestions(overview, locations, revenue_trend, events, bookings):
    """Generate revenue improvement suggestions based on data."""
    parts = []
    total_revenue = overview.get("total_revenue", 0)
    total_bookings = overview.get("total_bookings", 0)
    total_members = overview.get("total_members", 0)

    parts.append(f"Current revenue: ₹{total_revenue:,.0f} from {total_bookings} bookings.")

    # Revenue per booking
    if total_bookings > 0:
        rev_per_booking = total_revenue / total_bookings
        parts.append(f"Average revenue per booking: ₹{rev_per_booking:,.0f}. Increasing booking volume or pricing can boost revenue.")

    # Location revenue gaps
    if len(locations) >= 2:
        top = max(locations, key=lambda x: x.get("revenue", 0))
        low = min(locations, key=lambda x: x.get("revenue", 0))
        if top.get("revenue", 0) > 0 and low.get("revenue", 0) == 0:
            parts.append(f"{low['location_name']} has ₹0 revenue while {top['location_name']} generates ₹{top['revenue']:,.0f}. Focus on promoting {low['location_name']}.")

    # Revenue trend
    rev_values = revenue_trend.get("values", [])
    if len(rev_values) >= 2 and rev_values[-2] > 0:
        if rev_values[-1] < rev_values[-2]:
            parts.append(f"Revenue is declining (₹{rev_values[-2]:,.0f} → ₹{rev_values[-1]:,.0f}). Consider promotional discounts or events to attract more bookings.")

    # Events as revenue source
    if events:
        avg_collection = sum(e.get("total_collected", 0) for e in events) / len(events)
        if avg_collection == 0:
            parts.append(f"{len(events)} events organized but collected ₹0. Consider adding entry fees to events for additional revenue.")
        else:
            parts.append(f"Events generate avg ₹{avg_collection:,.0f} per event — organizing more paid events can supplement booking revenue.")

    # Member to revenue ratio
    if total_members > 0 and total_revenue > 0:
        rev_per_member = total_revenue / total_members
        parts.append(f"Revenue per member: ₹{rev_per_member:,.0f}. Engaging more members can directly increase revenue.")

    if len(parts) == 1:
        parts.append("To increase revenue: boost booking volume, optimize pricing, organize paid events, and promote underperforming locations.")

    return "Revenue Strategy: " + " ".join(parts)


def _booking_suggestions(overview, booking_trend, bookings):
    """Generate booking improvement suggestions based on data."""
    parts = []
    total = overview.get("total_bookings", 0)
    pending = overview.get("pending_bookings", 0)
    completed = overview.get("completed_bookings", 0)
    cancelled = overview.get("cancelled_bookings", 0)

    parts.append(f"Current: {total} bookings ({completed} completed, {pending} pending, {cancelled} cancelled).")

    if pending > completed and completed > 0:
        parts.append(f"Pending bookings ({pending}) exceed completed ({completed}). Follow up with members to convert pending to completed.")

    if cancelled > 0 and total > 0:
        cancel_rate = (cancelled / total * 100)
        parts.append(f"Cancellation rate: {cancel_rate:.0f}%. Investigate reasons and improve booking experience.")

    # Day-of-week analysis
    if len(bookings) >= 5:
        day_counts = Counter()
        for b in bookings:
            if b.get("booking_date"):
                day_counts[getdate(b["booking_date"]).strftime("%A")] += 1
        if day_counts:
            best_day, best_count = day_counts.most_common(1)[0]
            worst_day, worst_count = day_counts.most_common()[-1]
            parts.append(f"Peak day: {best_day} ({best_count} bookings). Promote bookings on low days like {worst_day} ({worst_count} bookings).")

    bk_totals = booking_trend.get("totals", [])
    if len(bk_totals) >= 2:
        if bk_totals[-1] < bk_totals[-2]:
            parts.append(f"Bookings declining ({bk_totals[-2]} → {bk_totals[-1]}). Consider promotions or discounts to reverse the trend.")

    if len(parts) == 1:
        parts.append("To increase bookings: offer promotions on low-activity days, follow up on pending bookings, and reduce cancellations.")

    return "Booking Strategy: " + " ".join(parts)


def _location_suggestions(locations):
    """Generate location improvement suggestions based on data."""
    parts = []
    if not locations:
        return "No location data available."

    sorted_locs = sorted(locations, key=lambda x: x.get("revenue", 0), reverse=True)
    top = sorted_locs[0]
    low = sorted_locs[-1]

    parts.append(f"Top: {top['location_name']} (₹{top['revenue']:,.0f} revenue, {top['total_bookings']} bookings).")

    if top.get("revenue", 0) > 0:
        parts.append(f"Replicate {top['location_name']}'s success at other locations.")

    if low.get("revenue", 0) == 0 and low["location_name"] != top["location_name"]:
        parts.append(f"{low['location_name']} has ₹0 revenue. Needs marketing push or better space offerings.")

    # Compare metrics
    for loc in sorted_locs:
        if loc.get("total_spaces", 0) > 0 and loc.get("total_bookings", 0) == 0:
            parts.append(f"{loc['location_name']} has {loc['total_spaces']} spaces but 0 bookings — spaces are not being utilized.")

    return "Location Strategy: " + " ".join(parts)


def _event_suggestions_text(overview, events, locations, bookings, space_dist):
    """Generate event suggestions as text for Q&A."""
    parts = []
    total_events = overview.get("total_events", 0)
    total_members = overview.get("total_members", 0)
    total_bookings = overview.get("total_bookings", 0)

    if total_events == 0:
        if total_members >= 3 and total_bookings >= 3:
            parts.append(f"No events organized despite {total_members} members and {total_bookings} bookings. Organize a community event to boost engagement.")
        else:
            parts.append("No events organized yet. Start with a community meetup to engage members.")
    else:
        completed = [e for e in events if e.get("event_status") == "Completed"]
        themes = Counter(e.get("event_theme") for e in completed if e.get("event_theme"))
        if themes:
            top_theme, count = themes.most_common(1)[0]
            if count >= 2:
                parts.append(f"'{top_theme}' has {count} successful events — repeat this proven theme.")
            if len(themes) == 1 and len(events) >= 3:
                parts.append(f"All events use the same theme. Diversify with networking, skill development, or wellness themes.")

    # Timing
    if len(bookings) >= 5:
        day_counts = Counter()
        for b in bookings:
            if b.get("booking_date"):
                day_counts[getdate(b["booking_date"]).strftime("%A")] += 1
        if day_counts:
            best_day, best_count = day_counts.most_common(1)[0]
            if best_count >= len(bookings) * 0.3:
                parts.append(f"Schedule events on {best_day}s — {best_count} out of {len(bookings)} bookings happen on this day.")

    # Location gaps
    locs_with_events = [l for l in locations if l.get("total_events", 0) > 0]
    locs_without = [l for l in locations if l.get("total_events", 0) == 0 and (l.get("total_members", 0) > 0 or l.get("total_bookings", 0) > 0)]
    if locs_with_events and locs_without:
        parts.append(f"Bring events to {locs_without[0]['location_name']} — it has active members but no events.")

    # Underutilized spaces
    space_labels = space_dist.get("labels", [])
    space_values = space_dist.get("values", [])
    if space_labels and len(bookings) >= 3:
        space_type_bookings = Counter()
        for b in bookings:
            if b.get("space_type"):
                space_type_bookings[b["space_type"]] += 1
        for i, label in enumerate(space_labels):
            if space_values[i] > 0 and space_type_bookings.get(label, 0) == 0:
                parts.append(f"{space_values[i]} {label} spaces have 0 bookings — use them for events.")
                break

    if not parts:
        parts.append("Organize events based on member activity patterns and underutilized spaces.")

    return "Event Strategy: " + " ".join(parts)


def _space_suggestions_text(labels, values, bookings):
    """Generate space utilization suggestions as text."""
    parts = []
    total_spaces = sum(values)
    parts.append(f"Total spaces: {total_spaces}.")

    space_type_bookings = Counter()
    for b in bookings:
        if b.get("space_type"):
            space_type_bookings[b["space_type"]] += 1

    for i, label in enumerate(labels):
        count = values[i]
        bk_count = space_type_bookings.get(label, 0)
        if count > 0 and bk_count == 0:
            parts.append(f"{label}: {count} spaces, 0 bookings — completely unused. Consider events or promotions.")
        elif count > 0 and bk_count > 0:
            util = bk_count / count
            if util < 0.5:
                parts.append(f"{label}: {count} spaces, {bk_count} bookings — underutilized. More capacity available.")
            else:
                parts.append(f"{label}: {count} spaces, {bk_count} bookings — well utilized.")

    return "Space Strategy: " + " ".join(parts)


@frappe.whitelist()
def get_event_suggestions(from_date=None, to_date=None, location=None):
    """Generate data-driven event suggestions. Only recommend when enough data exists."""
    _check_admin_role()
    suggestions = []

    # Gather data
    overview = get_analytics_overview(from_date, to_date, location)
    loc_stats = get_location_wise_stats(from_date, to_date)
    locations = loc_stats.get("locations", [])
    space_dist = get_space_type_distribution(location)
    events = get_events_list(from_date, to_date, location).get("events", [])
    bookings = get_recent_bookings(from_date, to_date, location, limit=200).get("bookings", [])
    booking_trend = get_booking_trend(from_date, to_date, location)
    revenue_trend = get_revenue_trend(from_date, to_date, location)

    space_labels = space_dist.get("labels", [])
    space_values = space_dist.get("values", [])
    total_members = overview.get("total_members", 0)
    total_events = overview.get("total_events", 0)
    total_bookings = overview.get("total_bookings", 0)
    total_revenue = overview.get("total_revenue", 0)

    # ── 1. Repeat successful event themes (needs >= 2 completed events with same theme) ──
    completed_events = [e for e in events if e.get("event_status") == "Completed"]
    if len(completed_events) >= 2:
        themes = Counter(e.get("event_theme") for e in completed_events if e.get("event_theme"))
        if themes:
            top_theme, top_count = themes.most_common(1)[0]
            if top_count >= 2:
                # Calculate actual revenue/collection from these events
                theme_events = [e for e in completed_events if e.get("event_theme") == top_theme]
                avg_collected = sum(e.get("total_collected", 0) for e in theme_events) / len(theme_events)
                avg_spent = sum(e.get("total_spent", 0) for e in theme_events) / len(theme_events)
                suggestions.append({
                    "category": "Event Type",
                    "title": f"Repeat '{top_theme}' Theme",
                    "description": (
                        f"'{top_theme}' has {top_count} completed events with "
                        f"avg collection ₹{avg_collected:,.0f} and avg spend ₹{avg_spent:,.0f}. "
                        f"This theme has proven demand — schedule another one."
                    ),
                    "confidence": "High",
                    "data_points": f"{top_count} completed events, avg collected ₹{avg_collected:,.0f}"
                })

    # ── 2. Optimal timing based on booking day-of-week (needs >= 5 bookings) ──
    if len(bookings) >= 5:
        day_counts = Counter()
        for b in bookings:
            if b.get("booking_date"):
                day_name = getdate(b["booking_date"]).strftime("%A")
                day_counts[day_name] += 1

        if day_counts:
            sorted_days = day_counts.most_common()
            best_day, best_count = sorted_days[0]
            worst_day, worst_count = sorted_days[-1]

            # Only suggest if there's a clear winner (>= 30% of bookings)
            if best_count >= len(bookings) * 0.3:
                suggestions.append({
                    "category": "Optimal Timing",
                    "title": f"Schedule Events on {best_day}s",
                    "description": (
                        f"{best_day} has {best_count} out of {len(bookings)} bookings ({best_count/len(bookings)*100:.0f}%). "
                        f"This is when members are most active — events on this day will get better attendance."
                    ),
                    "confidence": "High",
                    "data_points": f"{best_count}/{len(bookings)} bookings on {best_day}s"
                })

            # Only suggest avoiding if there's a clear loser (< 15% of bookings)
            if worst_count > 0 and worst_count < len(bookings) * 0.15:
                suggestions.append({
                    "category": "Optimal Timing",
                    "title": f"Avoid {worst_day}s for Major Events",
                    "description": (
                        f"{worst_day} has only {worst_count} out of {len(bookings)} bookings "
                        f"({worst_count/len(bookings)*100:.0f}%). Member activity is low — "
                        f"save major events for busier days."
                    ),
                    "confidence": "Medium",
                    "data_points": f"{worst_count}/{len(bookings)} bookings on {worst_day}s"
                })

    # ── 3. Growing momentum (needs >= 3 months of booking data with upward trend) ──
    bk_totals = booking_trend.get("totals", [])
    bk_labels = booking_trend.get("labels", [])
    if len(bk_totals) >= 3:
        # Check if last 3 months show upward trend
        last_three = bk_totals[-3:]
        if last_three[2] > last_three[0] and last_three[2] > last_three[1]:
            growth_pct = ((last_three[2] - last_three[0]) / last_three[0] * 100) if last_three[0] else 0
            suggestions.append({
                "category": "Optimal Timing",
                "title": f"Capitalize on Booking Growth in {bk_labels[-1]}",
                "description": (
                    f"Bookings grew from {last_three[0]} to {last_three[2]} over the last 3 months "
                    f"({growth_pct:.0f}% increase). Member activity is rising — "
                    f"this is the right time to announce events."
                ),
                "confidence": "High",
                "data_points": f"{last_three[0]} → {last_three[1]} → {last_three[2]} bookings"
            })

    # ── 4. Underutilized spaces (needs actual booking + space data) ──
    if space_labels and space_values and len(bookings) >= 3:
        total_spaces = sum(space_values)
        # Count bookings per space type
        space_type_bookings = Counter()
        for b in bookings:
            if b.get("space_type"):
                space_type_bookings[b["space_type"]] += 1

        for i, label in enumerate(space_labels):
            space_count = space_values[i]
            booking_count = space_type_bookings.get(label, 0)
            # Low utilization = has spaces but very few bookings relative to space count
            if space_count > 0 and booking_count == 0:
                pct = (space_count / total_spaces * 100) if total_spaces else 0
                suggestions.append({
                    "category": "Space Utilization",
                    "title": f"Use {label}s for Events — Zero Bookings",
                    "description": (
                        f"There are {space_count} {label} spaces ({pct:.0f}% of total) but "
                        f"0 bookings in this period. These spaces are completely unused — "
                        f"hosting events here can generate revenue from idle assets."
                    ),
                    "confidence": "High",
                    "data_points": f"{space_count} {label} spaces, 0 bookings"
                })
            elif space_count > 0 and booking_count > 0:
                utilization = booking_count / space_count
                if utilization < 0.5:
                    suggestions.append({
                        "category": "Space Utilization",
                        "title": f"{label}s Are Underutilized",
                        "description": (
                            f"{space_count} {label} spaces with only {booking_count} bookings "
                            f"({utilization:.1f} bookings per space). These spaces have capacity "
                            f"for events without disrupting regular bookings."
                        ),
                        "confidence": "Medium",
                        "data_points": f"{space_count} spaces, {booking_count} bookings"
                    })

    # ── 5. No events but active members (needs members + bookings data) ──
    if total_events == 0 and total_members >= 3 and total_bookings >= 3:
        suggestions.append({
            "category": "Event Type",
            "title": "Organize a Community Event",
            "description": (
                f"0 events organized despite {total_members} members and {total_bookings} bookings. "
                f"Members are actively using spaces but have no community events. "
                f"A networking or meetup event can boost engagement and retention."
            ),
            "confidence": "High",
            "data_points": f"0 events, {total_members} members, {total_bookings} bookings"
        })

    # ── 6. Location gap (needs >= 2 locations with real event data) ──
    if len(locations) >= 2:
        locs_with_events = [l for l in locations if l.get("total_events", 0) > 0]
        locs_without_events = [l for l in locations if l.get("total_events", 0) == 0]
        if locs_with_events and locs_without_events:
            top_loc = max(locs_with_events, key=lambda x: x.get("total_events", 0))
            for low_loc in locs_without_events:
                # Only suggest if the location has members or bookings
                if low_loc.get("total_members", 0) > 0 or low_loc.get("total_bookings", 0) > 0:
                    suggestions.append({
                        "category": "Location Strategy",
                        "title": f"Bring Events to {low_loc['location_name']}",
                        "description": (
                            f"{top_loc['location_name']} has hosted {top_loc['total_events']} events, "
                            f"but {low_loc['location_name']} has hosted 0 despite having "
                            f"{low_loc.get('total_members', 0)} members and {low_loc.get('total_bookings', 0)} bookings. "
                            f"Members at this location are missing out on community events."
                        ),
                        "confidence": "High",
                        "data_points": (
                            f"{top_loc['location_name']}: {top_loc['total_events']} events | "
                            f"{low_loc['location_name']}: 0 events, "
                            f"{low_loc.get('total_members', 0)} members, "
                            f"{low_loc.get('total_bookings', 0)} bookings"
                        )
                    })

    # ── 7. Revenue opportunity from events (needs revenue + event data) ──
    if total_revenue > 0 and total_events > 0:
        rev_values = revenue_trend.get("values", [])
        rev_labels = revenue_trend.get("labels", [])
        if len(rev_values) >= 2:
            # If revenue is declining, suggest events as revenue boost
            if rev_values[-1] < rev_values[-2] and rev_values[-2] > 0:
                decline_pct = ((rev_values[-2] - rev_values[-1]) / rev_values[-2] * 100)
                suggestions.append({
                    "category": "Revenue Strategy",
                    "title": f"Use Events to Offset Revenue Decline in {rev_labels[-1]}",
                    "description": (
                        f"Revenue dropped {decline_pct:.0f}% from ₹{rev_values[-2]:,.0f} to ₹{rev_values[-1]:,.0f}. "
                        f"Paid events can supplement space booking revenue. "
                        f"Past events collected an average of "
                        f"₹{sum(e.get('total_collected',0) for e in events)/len(events):,.0f} per event."
                    ),
                    "confidence": "High",
                    "data_points": (
                        f"Revenue: ₹{rev_values[-2]:,.0f} → ₹{rev_values[-1]:,.0f} | "
                        f"{total_events} past events"
                    )
                })

    # ── 8. Diversify themes (needs >= 3 events all with same theme) ──
    if len(events) >= 3:
        themes = Counter(e.get("event_theme") for e in events if e.get("event_theme"))
        if themes:
            top_theme, top_count = themes.most_common(1)[0]
            if top_count >= 3 and len(themes) == 1:
                suggestions.append({
                    "category": "Theme",
                    "title": "Diversify Event Themes",
                    "description": (
                        f"All {len(events)} events used the same theme '{top_theme}'. "
                        f"Member preferences may vary — try new themes like networking, "
                        f"skill development, or wellness to attract different segments."
                    ),
                    "confidence": "Medium",
                    "data_points": f"{len(events)} events, 1 unique theme"
                })

    return {"suggestions": suggestions}
