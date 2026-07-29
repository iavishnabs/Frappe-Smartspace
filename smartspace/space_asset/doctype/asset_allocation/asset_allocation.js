// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Allocation", {
	onload: function (frm) {
		frm.set_query("location", function () {
			return { filters: [["Location", "status", "=", "Active"]] };
		});
		frm.set_query("floor", function () {
			return { filters: [["Floor", "location", "=", frm.doc.location]] };
		});
		frm.set_query("space", function () {
			return { filters: [["Space", "floor", "=", frm.doc.floor]] };
		});
		frm.set_query("asset", "assets", function () {
			return { filters: [["Asset", "status", "=", "Available"]] };
		});
	},
	location: function (frm) {
		frm.set_value("floor", "");
		frm.set_value("space", "");
	},
	floor: function (frm) {
		frm.set_value("space", "");
	}
});
