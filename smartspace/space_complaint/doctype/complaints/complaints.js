// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Complaints", {
	refresh(frm) {
        if (
            frm.doc.complaint_type === "Asset Related" &&
            frm.doc.related_asset
        ) {
            frm.set_df_property("complaint_type", "read_only", 1);
            frm.set_df_property("related_asset", "read_only", 1);
        }
         if (
            frm.doc.complaint_type === "Asset Related" &&
            !frm.doc.assigned_to &&
            (frappe.user.has_role("Supervisor") || frappe.session.user === "Administrator")
        ) {

            frm.add_custom_button(__("Assign Technician"), function () {

                let d = new frappe.ui.Dialog({
                    title: "Assign Technician",
                    fields: [
                        {
                            label: "Reported Date",
                            fieldname: "reported_date",
                            fieldtype: "Date",
                            reqd: 1,
                            default: frappe.datetime.get_today()
                        },
                        {
                            label: "Priority",
                            fieldname: "priority",
                            fieldtype: "Select",
                            options: "Low\nMedium\nHigh",
                            reqd: 1
                        },
                        {
                            label: "Task Description",
                            fieldname: "task_description",
                            fieldtype: "Small Text",
                            reqd: 1
                        }
                    ],
                    primary_action_label: "Assign",
                    primary_action(values) {

                        frappe.call({
                            method: "smartspace.space_complaint.doctype.complaints.complaints.assign_technician",
                            args: {
                                complaint: frm.doc.name,
                                reported_date: values.reported_date,
                                priority: values.priority,
                                task_description: values.task_description
                            },
                         callback: function(r) {
                            if (r.message && r.message.success === false) {
                                frappe.msgprint(r.message.message);
                                return;
                            }
                            frappe.msgprint("Technician Assigned Successfully");
                            frm.reload_doc();
                            d.hide();
                        }
                        });
                    }
                });

                d.show();

            });
        }
    }
});
