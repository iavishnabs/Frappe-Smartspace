// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Maintenance", {
	onload: function (frm) {
		frm.set_query("asset", function () {
			return { filters: [["Asset", "status", "=", "Available"]] };
		});
	},
	refresh: function (frm) {
		frm.set_query("asset", function () {
			return { filters: [["Asset", "status", "=", "Available"]] };
		});
	},
});
