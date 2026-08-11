{
    "name": "Custom HR KPI",
    "version": "1.0.0",
    "category": "Human Resources",
    "sequence": 1,
    "summary": "Custom HR KPI Module for Odoo v17",
    "description": """Custom HR KPI Module for Odoo v17.
    
    This module provides functionality for tracking and managing HR Key Performance Indicators (KPIs).""",
    "depends": [
        "hr",
        "mail",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_kpi_sequence.xml",
        "report/hr_kpi_excel_report_abs.xml",
        "views/hr_kpi_views.xml",
        "views/hr_kpi_type_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
