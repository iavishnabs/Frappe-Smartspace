// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Task Allocation", {
    refresh(frm) {
        let can_access = frappe.user.has_role("Technician") || frappe.session.user === "Administrator";
        let can_supervise = frappe.user.has_role("Supervisor") || frappe.session.user === "Administrator";

        if (can_access && frm.doc.status === "Open") {
            let start_btn = frm.add_custom_button(__("Start"), function () {
                frappe.call({
                    method: "smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation.start_work",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Work Started");
                            frm.reload_doc();
                        }
                    }
                });
            });
            $(start_btn).removeClass("btn-default").addClass("btn-dark").css("--hover-bg", "inherit");
        }

        if (can_access && frm.doc.status === "In Progress") {
            let finish_btn = frm.add_custom_button(__("Finish"), function () {
                frappe.call({
                    method: "smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation.finish_work",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Work Completed");
                            frm.reload_doc();
                        }
                    }
                });
            });
            $(finish_btn).removeClass("btn-default").addClass("btn-dark");

            let flag_btn = frm.add_custom_button(__("Flag Unusable"), function () {
                frappe.call({
                    method: "smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation.flag_unusable",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Asset Flagged as Unusable - Supervisor Notified");
                            frm.reload_doc();
                        }
                    }
                });
            });
            $(flag_btn).removeClass("btn-default").addClass("btn-dark");
        }

        if (can_supervise && frm.doc.status === "Flagged") {
            let approve_btn = frm.add_custom_button(__("Approve Decommission"), function () {
                let d = new frappe.ui.Dialog({
                    title: "Approve Decommission",
                    fields: [
                        {
                            label: "Closed Reason",
                            fieldname: "closed_reason",
                            fieldtype: "Small Text",
                            reqd: 1
                        }
                    ],
                    primary_action_label: "Approve",
                    primary_action(values) {
                        frappe.call({
                            method: "smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation.approve_decommission",
                            args: { name: frm.doc.name, closed_reason: values.closed_reason },
                            callback: function (r) {
                                if (r.message) {
                                    frappe.msgprint("Asset Decommissioned");
                                    frm.reload_doc();
                                    d.hide();
                                }
                            }
                        });
                    }
                });
                d.show();
            });
            $(approve_btn).removeClass("btn-default").addClass("btn-dark");

            let reject_btn = frm.add_custom_button(__("Reject Flag"), function () {
                frappe.call({
                    method: "smartspace.space_asset.doctype.maintenance_task_allocation.maintenance_task_allocation.reject_flag",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint("Flag Rejected - Resume Work");
                            frm.reload_doc();
                        }
                    }
                });
            });
            $(reject_btn).removeClass("btn-default").addClass("btn-dark");
        }
    }
});
