// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset", {
	refresh(frm) {
        frm.add_custom_button(__("Raise Complaint"), function () {

            frappe.new_doc("Complaints", {
                complaint_type: "Asset Related",
                related_asset: frm.doc.name,
                raised_by: frappe.session.user
            });

        });

        if (frm.doc.__islocal) return;

        render_asset_movements(frm);
    }
});

function render_asset_movements(frm) {
    frappe.call({
        method: "smartspace.space_asset.doctype.asset.asset.get_asset_movements",
        args: { asset: frm.doc.name },
        callback: function(r) {
            var allocations = r.message || [];

            if (allocations.length === 0) {
                frm.fields_dict.asset_allocation.$wrapper.html(
                    '<p style="color:#888;padding:12px;">No asset movement history found.</p>'
                );
                return;
            }

            var rows = [];
            var prev_location = null;
            for (var i = allocations.length - 1; i >= 0; i--) {
                var a = allocations[i];
                if (prev_location !== null && a.location === prev_location) {
                    continue;
                }
                rows.push({
                    from: prev_location || "-",
                    to: a.location || "-",
                    move_from: a.allocated_from ? frappe.datetime.str_to_user(a.allocated_from) : "-",
                    move_to: a.allocated_to ? frappe.datetime.str_to_user(a.allocated_to) : "-",
                    allocation: a.name
                });
                prev_location = a.location;
            }
            rows.reverse();

            if (rows.length === 0) {
                frm.fields_dict.asset_allocation.$wrapper.html(
                    '<p style="color:#888;padding:12px;">No location changes in asset allocation history.</p>'
                );
                return;
            }

            var html = '<div style="padding:8px 0;">';
            html += '<table class="table table-bordered table-striped" style="margin:0;">';
            html += '<thead><tr style="background:#f8f8f8;">';
            html += '<th style="width:20%;">Allocation ID</th>';
            html += '<th style="width:20%;">From Location</th>';
            html += '<th style="width:20%;">To Location</th>';
            html += '<th style="width:15%;">Move From</th>';
            html += '<th style="width:15%;">Move To</th>';
            html += '</tr></thead><tbody>';

            for (var j = 0; j < rows.length; j++) {
                var row = rows[j];
                html += '<tr>';
                html += '<td><a href="/app/asset-allocation/' + row.allocation + '">' + row.allocation + '</a></td>';
                html += '<td>' + row.from + '</td>';
                html += '<td>' + row.to + '</td>';
                html += '<td>' + row.move_from + '</td>';
                html += '<td>' + row.move_to + '</td>';
                html += '</tr>';
            }

            html += '</tbody></table></div>';
            frm.fields_dict.asset_allocation.$wrapper.html(html);
        }
    });
}
