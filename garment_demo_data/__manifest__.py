# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Demo Data: Nelsis Smart Garment — Suite-Wide Demonstration Dataset
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Demo Data (Full Suite)',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'One interlinked demo dataset spanning all 28 Nelsis Smart Garment modules',
    'description': """
Nelsis Smart Garment — Suite-Wide Demo Data
=============================================
Installs one coherent, cross-linked demonstration dataset across every module of the
Nelsis Smart Garment suite: 2 buyers, 3 styles/orders, 2 suppliers, ~10 employees, and
the full downstream chain (techpack, BOM, sample, costing, PLM, merchandising, TNA,
purchase, production, quality, IE, maintenance, logistics, commercial/export, finance,
compliance, document management, buyer portal, analytics, mobile, AI, IoT) all
referencing the same buyers/styles/orders so the whole suite can be demoed end-to-end.

Install this module ONLY on a demo/staging/training database — it is not intended for
a production database. Uninstalling it removes all the demo records it created.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'garment_buyer_crm', 'garment_style_library', 'garment_hr', 'garment_supplier',
        'garment_warehouse', 'garment_techpack', 'garment_bom_management',
        'garment_sample_management', 'garment_costing', 'garment_plm',
        'garment_merchandising', 'garment_order_management', 'garment_tna',
        'garment_purchase', 'garment_production', 'garment_quality',
        'garment_ie_management', 'garment_maintenance', 'garment_logistics',
        'garment_commercial_export', 'garment_finance', 'garment_compliance',
        'garment_document_management', 'garment_buyer_portal', 'garment_analytics_bi',
        'garment_mobile_platform', 'garment_ai_intelligence', 'garment_iot_platform',
    ],
    'data': [
        'data/01_buyer_crm_demo.xml',
        'data/01_style_library_demo.xml',
        'data/01_hr_demo.xml',
        'data/01_supplier_demo.xml',
        'data/01_warehouse_demo.xml',
        'data/02_techpack_demo.xml',
        'data/02_bom_demo.xml',
        'data/02_sample_demo.xml',
        'data/02_costing_demo.xml',
        'data/02_plm_demo.xml',
        'data/03_merchandising_demo.xml',
        'data/03_order_demo.xml',
        'data/03_tna_demo.xml',
        'data/03_purchase_demo.xml',
        'data/04_production_demo.xml',
        'data/04_quality_demo.xml',
        'data/04_ie_demo.xml',
        'data/04_maintenance_demo.xml',
        'data/04_logistics_demo.xml',
        'data/04_commercial_export_demo.xml',
        'data/05_finance_demo.xml',
        'data/05_compliance_demo.xml',
        'data/05_document_management_demo.xml',
        'data/05_buyer_portal_demo.xml',
        'data/05_analytics_bi_demo.xml',
        'data/05_mobile_platform_demo.xml',
        'data/05_ai_intelligence_demo.xml',
        'data/05_iot_platform_demo.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
