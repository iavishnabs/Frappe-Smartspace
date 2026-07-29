// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Space Event", {
	refresh(frm) {
		if (frm.doc.event_status === "Draft") {
			let btn = frm.add_custom_button(__("Publish"), function () {
				frappe.call({
					method: "smartspace.space_event.doctype.space_event.space_event.publish_event",
					args: { name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint("Event published. Members and staff notified.");
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
