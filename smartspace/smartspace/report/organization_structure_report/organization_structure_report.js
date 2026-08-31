// Copyright (c) 2026, avishna and contributors
// For license information, please see license.txt

frappe.query_reports["Organization Structure Report"] = {
	"onload": function() {
		const style = document.createElement("style");
		style.textContent = `
			.query-report .datatable { z-index: 1 !important; }
			.query-report .datatable .dt-scrollable { z-index: 1 !important; }
			.query-report .datatable .dt-header { z-index: 1 !important; }
			.query-report .datatable thead { z-index: 1 !important; }
			.query-report .datatable th { z-index: 1 !important; position: relative !important; }
			.query-report .report-datatable { z-index: 1 !important; }
			.query-report .dt-scrollableContainer { z-index: 1 !important; position: relative !important; }
			.modal { z-index: 9999 !important; }
			.awesomplete { z-index: 1060 !important; }
			.awesomplete > ul { z-index: 1061 !important; }
			body > .awesomplete { z-index: 1060 !important; }
			ul.awesomplete { z-index: 1060 !important; }
			.dropdown-menu { z-index: 1060 !important; }
			.frappe-control { z-index: auto !important; }
		`;
		document.head.appendChild(style);
	},
	"filters": [
		{
			"fieldname": "organization",
			"label": __("Organization"),
			"fieldtype": "Link",
			"options": "Organization",
			"width": "80"
		},
		{
			"fieldname": "location",
			"label": __("Location"),
			"fieldtype": "Link",
			"options": "Location",
			"width": "80"
		},
		{
			"fieldname": "location_status",
			"label": __("Location Status"),
			"fieldtype": "Select",
			"options": "\nActive\nInactive",
			"width": "80"
		}
	]
};
