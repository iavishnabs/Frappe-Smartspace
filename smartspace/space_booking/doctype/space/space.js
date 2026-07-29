// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.ui.form.on('Space', {

    setup: function (frm) {

        frm.set_query('floor', function () {

            // if location not selected, return empty filter safely
            if (!frm.doc.location) {
                return {
                    filters: {
                        name: ["=", ""]   // returns no floors
                    }
                };
            }

            return {
                filters: {
                    location: frm.doc.location
                }
            };
        });

    },

    location: function (frm) {
        frm.set_value('floor', null);
    }

});