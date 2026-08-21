import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.redirect("/signin")
    context.active = "ai-chatbot"
