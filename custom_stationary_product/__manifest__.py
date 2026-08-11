# -*- coding: utf-8 -*-
{
    'name': 'Custom Stationary Product',
    'version': '17.0.1.0.0',
    'summary': 'Manage Stationary Products separately from Inventory',
    'description': """
        This module adds Stationary Product management feature:
        - Mark products as Stationary Product via a boolean field
        - Separate menu under HR > Employees for Stationary Products
        - Stationary Products are hidden from Inventory > Products
    """,
    'category': 'Human Resources',
    'author': 'Nelsis Tech Limited',
    'website': 'https://www.nelsis.com',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'stock',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/stationary_product_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
