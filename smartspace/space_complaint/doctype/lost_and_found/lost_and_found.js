// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Lost And Found", {
	refresh(frm) {
		if (frm.doc.status === "Open") {
			let btn = frm.add_custom_button(__("Mark Returned"), function () {
				show_return_dialog(frm);
			});
			style_black_button(btn);
		}

		if (frm.doc.status === "Returned") {
			let btn = frm.add_custom_button(__("Close"), function () {
				frappe.call({
					method: "smartspace.space_complaint.doctype.lost_and_found.lost_and_found.close_report",
					args: { name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint("Report closed");
							frm.reload_doc();
						}
					}
				});
			});
			style_black_button(btn);
		}
	}
});

function show_return_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: "Mark Returned",
		fields: [
			{
				label: "Matched Lost Report",
				fieldname: "lost_report",
				fieldtype: "Link",
				options: "Lost And Found",
				get_query: function () {
					return {
						filters: [
							["Lost And Found", "report_type", "=", "Lost"],
							["Lost And Found", "status", "=", "Open"],
							["Lost And Found", "name", "!=", frm.doc.name]
						]
					};
				}
			},
			{
				label: "Returned To",
				fieldname: "returned_to",
				fieldtype: "Link",
				options: "App User",
				reqd: 1
			}
		],
		primary_action_label: "Mark Returned",
		primary_action: function (values) {
			frappe.call({
				method: "smartspace.space_complaint.doctype.lost_and_found.lost_and_found.mark_returned",
				args: {
					found_report: frm.doc.name,
					lost_report: values.lost_report || "",
					returned_to: values.returned_to
				},
				callback: function (r) {
					if (r.message) {
						dialog.hide();
						frappe.msgprint("Item marked as returned");
						frm.reload_doc();
					}
				}
			});
		}
	});
	dialog.show();
}

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
