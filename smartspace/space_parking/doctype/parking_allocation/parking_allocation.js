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

		if (!frm.is_new()) {
			let btn = frm.add_custom_button(__("Find Vehicle"), function () {
				show_find_vehicle_dialog();
			});
			style_black_button(btn);
		}
	}
});

function show_find_vehicle_dialog() {
	let dialog = new frappe.ui.Dialog({
		title: "Find Vehicle",
		fields: [
			{
				label: "Vehicle Number",
				fieldname: "vehicle_number",
				fieldtype: "Data",
				reqd: 1
			}
		],
		primary_action_label: "Search",
		primary_action: function (values) {
			frappe.call({
				method: "smartspace.space_parking.doctype.parking_allocation.parking_allocation.find_vehicle",
				args: { vehicle_number: values.vehicle_number },
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						let html = "<table class='table table-bordered'><thead><tr><th>Slot</th><th>Vehicle</th><th>Member</th><th>Parked Since</th></tr></thead><tbody>";
						r.message.forEach(function (row) {
							html += `<tr><td>${row.parking_slot}</td><td>${row.vehicle_number}</td><td>${row.member || "-"}</td><td>${row.allocated_from}</td></tr>`;
						});
						html += "</tbody></table>";
						dialog.set_title("Search Results");
						dialog.fields_dict.vehicle_number.$wrapper.html(html);
					} else {
						frappe.msgprint("No active parking found for that vehicle number");
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
