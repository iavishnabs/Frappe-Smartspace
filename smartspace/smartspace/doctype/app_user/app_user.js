// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("App User", {
	refresh(frm) {
        setup_field_queries(frm);
		set_full_name(frm);
	},
    
    first_name(frm) {
		set_full_name(frm);
	},

	last_name(frm) {
		set_full_name(frm);
	},
});

function setup_field_queries(frm) {
	frm.set_query("role", function() {
		return {
			filters: { is_custom: 1 }
		};
	});
}

function set_full_name(frm) {
	const first_name = (frm.doc.first_name || "").trim();
	const last_name = (frm.doc.last_name || "").trim();
	const full_name = [first_name, last_name].filter(Boolean).join(" ");
	frm.set_value("full_name", full_name);
}