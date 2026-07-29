// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Member", {
	onload: function (frm) {
		frm.set_query("app_user", function () {
			return { filters: [["App User", "role", "=", "Member"]] };
		});
	}
});
