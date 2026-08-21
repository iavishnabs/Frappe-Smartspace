// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Parking Allocation", {
	refresh(frm) {
		frm.set_query("parking_slot", function () {
			return { filters: [["Parking Slot", "status", "=", "Available"]] };
		});

		if (frm.doc.allocation_status === "Active" && !frm.is_new()) {
			let btn = frm.add_custom_button(__("Release"), function () {
				frappe.call({
					method: "smartspace.space_parking.doctype.parking_allocation.parking_allocation.release_parking",
					args: { name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint("Parking released");
							frm.reload_doc();
						}
					}
				});
			});
			style_black_button(btn);
		}
	}
});

function style_black_button(btn) {
	$(btn)
		.removeClass("btn-default btn-primary")
		.addClass("btn-dark")
		.css({
			"background-color": "#000000",
			"color": "#ffffff",
			"border": "1px solid #000000",
			"transition": "none"
		});

	$(btn).on("mouseenter mouseleave", function (e) {
		$(this).css({
			"background-color": "#000000",
			"color": "#ffffff",
			"border": "1px solid #000000"
		});
	});
}
