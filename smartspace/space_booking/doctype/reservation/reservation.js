// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reservation", {
	refresh(frm) {
		if (frm.doc.booking_status === "Pending") {
			let btn = frm.add_custom_button(__("Confirm"), function () {
				frappe.call({
					method: "smartspace.space_booking.doctype.reservation.reservation.confirm_reservation",
					args: { name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint("Reservation confirmed");
							frm.reload_doc();
						}
					}
				});
			});
			$(btn).removeClass("btn-default").addClass("btn-primary");
		}

		if (frm.doc.payment_status === "Pending" && frm.doc.payment) {
			let btn = frm.add_custom_button(__("Pay Now"), function () {
				frappe.call({
					method: "smartspace.space_booking.doctype.reservation.reservation.pay_now",
					args: { reservation_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint("Payment completed: " + r.message);
							frm.reload_doc();
						}
					}
				});
			});
			$(btn).removeClass("btn-default").addClass("btn-primary");
		}
	}
});
