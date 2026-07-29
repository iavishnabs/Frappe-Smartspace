// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset", {
	refresh(frm) {
        frm.add_custom_button(__("Raise Complaint"), function () {

            frappe.new_doc("Complaints", {
                complaint_type: "Asset Related",
                related_asset: frm.doc.name,
                raised_by: frappe.session.user
            });

        });
    }
});
