# -*- coding: utf-8 -*-
{
    'name': 'Grameen Cybernet ERM - Lead to Billing',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Lead > Approval > Survey > Technical Costing > Proposal > '
               'Work Order > Inventory > Installation > Billing',
    'description': """
Grameen Cybernet ERM - Lead to Billing System
=============================================

A business-process layer on top of Odoo Community 17 that digitises and
controls the complete flow from sales lead generation to customer billing.

Key capabilities
----------------
* Lead capture with configurable sequence and HOD approval gate
* Survey generation and technical survey with GPS / feasibility capture
* BOQ with configurable costing and margin methods, version-controlled
* Technical report submission back to Sales
* Proposal preparation, HOD / amount-based approval, revision versioning
* Native Odoo Sales Quotation and Sales Order integration
* Work Order with implementation team assignment
* Inventory availability check, reservation and delivery via Odoo Stock
* Procurement requests and RFQ / Purchase Order integration
* Installation with configurable checklist, photos and reports
* Revisit management preserving previous reports
* Billing eligibility control and Odoo Accounting invoice integration
* Role based security, record rules and full audit trail
* Management, Sales, Technical, Implementation, Inventory and Finance dashboards
* SLA / aging tracking with scheduled jobs and notifications
""",
    'author': 'Grameen Cybernet',
    'website': 'https://www.grameencybernet.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'contacts',
        'crm',
        'sale_management',
        'stock',
        'purchase',
        'account',
        'project',
        'board',
    ],
    'data': [
        'security/gc_erm_groups.xml',
        'security/ir.model.access.csv',
        'security/gc_erm_record_rules.xml',
        'data/gc_erm_sequence.xml',
        'data/gc_erm_config_data.xml',
        'data/gc_erm_mail_template.xml',
        'data/gc_erm_cron.xml',
        'views/gc_erm_config_views.xml',
        'views/gc_status_history_views.xml',
        'views/gc_lead_views.xml',
        'views/gc_survey_views.xml',
        'views/gc_boq_views.xml',
        'views/gc_technical_report_views.xml',
        'views/gc_proposal_views.xml',
        'views/gc_work_order_views.xml',
        'views/gc_procurement_views.xml',
        'views/gc_installation_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/gc_reason_wizard_views.xml',
        'wizard/gc_survey_assign_wizard_views.xml',
        'wizard/gc_acceptance_wizard_views.xml',
        'wizard/gc_procurement_po_wizard_views.xml',
        'wizard/gc_revisit_wizard_views.xml',
        'wizard/gc_invoice_wizard_views.xml',
        'views/gc_dashboard_views.xml',
        'views/gc_erm_menus.xml',
        'reports/gc_report_layout.xml',
        'reports/gc_report_actions.xml',
        'reports/gc_lead_report.xml',
        'reports/gc_survey_report.xml',
        'reports/gc_boq_report.xml',
        'reports/gc_technical_report_report.xml',
        'reports/gc_proposal_report.xml',
        'reports/gc_work_order_report.xml',
        'reports/gc_procurement_report.xml',
        'reports/gc_installation_report.xml',
    ],
    'demo': [
        'demo/gc_erm_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gc_erm_lead_to_billing/static/src/scss/gc_erm.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
