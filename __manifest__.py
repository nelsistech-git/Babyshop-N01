# -*- coding: utf-8 -*-
{
    'name': 'Real Estate Project Management',
    'version': '17.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Real Estate Project, Land Acquisition, Construction, Sales, '
                'Collection & Handover Management for Odoo Community 17',
    'description': """
Real Estate Project Management
===============================
A production-ready Real Estate Project & Property Management ERP for
Odoo Community 17. Manages the full lifecycle from land acquisition and
landowner agreements through construction, quality control, sales,
installment collection, rental and final handover.

Phase 1 - Foundation
--------------------
* Module architecture & security
* Land Owner Management
* Land Management
* Land Owner Agreement Management

Developed by: Nur Uddin Ahammed
Company: Nelsis Tech (https://www.nelsistech.com)
""",
    'author': 'Nur Uddin Ahammed, Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'analytic',
        'product',
        'uom',
    ],
    'data': [
        # Security
        'security/real_estate_security.xml',
        'security/ir.model.access.csv',
        'security/real_estate_record_rules.xml',
        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        # Views
        # NOTE (2026-08-15): VIEW FILES REORDERED. Odoo parses these XML files
        # top-to-bottom, and several files reference actions/views defined in
        # files that were listed LATER, which made installation fail with
        # 'External ID not found in the system: ...action_...'. The files were
        # topologically sorted so every referenced action/view is defined BEFORE
        # the file that uses it (verified with a full dependency analysis;
        # real_estate_menus.xml must always load last since it references every
        # action). Files affected: real_estate_installment_plan_views.xml,
        # real_estate_collection_views.xml, real_estate_warranty_views.xml,
        # real_estate_defect_views.xml, real_estate_booking_views.xml,
        # real_estate_sale_agreement_views.xml, real_estate_rent_schedule_views.xml,
        # real_estate_handover_views.xml, real_estate_project_views.xml,
        # real_estate_qc_inspection_views.xml, real_estate_rental_agreement_views.xml,
        # real_estate_dashboard_views.xml, real_estate_unit_views.xml.
        'views/real_estate_land_owner_views.xml',
        'views/real_estate_land_views.xml',
        'views/real_estate_land_agreement_views.xml',
        'views/real_estate_installment_plan_views.xml',
        'views/real_estate_collection_views.xml',
        'views/real_estate_warranty_views.xml',
        'views/real_estate_building_views.xml',
        'views/real_estate_block_views.xml',
        'views/real_estate_floor_views.xml',
        'views/real_estate_budget_views.xml',
        'views/real_estate_budget_transfer_views.xml',
        'views/real_estate_work_package_views.xml',
        'views/real_estate_boq_views.xml',
        'views/real_estate_contractor_views.xml',
        'views/real_estate_contractor_bill_views.xml',
        'views/real_estate_requisition_views.xml',
        'views/real_estate_site_report_views.xml',
        'views/real_estate_qc_checklist_template_views.xml',
        'views/real_estate_defect_views.xml',
        'views/real_estate_booking_views.xml',
        'views/real_estate_sale_agreement_views.xml',
        'views/real_estate_rent_schedule_views.xml',
        'views/res_partner_views.xml',
        'views/real_estate_handover_views.xml',
        'views/real_estate_project_views.xml',
        'views/real_estate_qc_inspection_views.xml',
        'views/real_estate_rental_agreement_views.xml',
        'views/real_estate_dashboard_views.xml',
        'views/real_estate_unit_views.xml',
        'views/real_estate_menus.xml',
        'report/real_estate_handover_report.xml',
        'report/real_estate_handover_templates.xml',
        'report/real_estate_reports.xml',
        'report/real_estate_report_templates.xml',
    ],
    'demo': [
        'demo/real_estate_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
