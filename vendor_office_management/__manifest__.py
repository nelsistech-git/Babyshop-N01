# -*- coding: utf-8 -*-
{
    'name': 'Vendor Office Management',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Vendors',
    'summary': 'Manage Office Vendors separately under Vendor menu',
    'description': """
        This module adds an Office Vendor classification to vendors.
        - Adds is_office_vendor boolean field on res.partner
        - Adds Office Vendors menu under Vendors in Invoicing
        - Shows only office vendors in a dedicated Kanban/List view
    """,
    'author': 'Nelsis Limited',
    'depends': ['account','custom_hr_employee'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/office_vendor_menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
