# -*- coding: utf-8 -*-

{
    'name': 'Odoo 17 Budget Management',
    'version': '17.0.1.0.1',
    'category': 'Accounting',
    'summary': """ Budget Management for Odoo 17 Community Edition. """,
    'description': """ This module allows accountants to manage analytic and 
    budgets. Once the Budgets are defined (in Accounting/Accounting/Budgets),
    the Project Managers can set the planned amount on each Analytic Account.
    The accountant has the possibility to see the total of amount planned for
    each Budget in order to ensure the total planned is not greater/lower 
    than what he planned for this Budget. Each list of record can also be 
    switched to a graphical view of it, odoo17, accounting, odoo17 accounting, odoo17 budget, odoo17""",
    'author': 'Nelsis Tech Limited',
    'website': 'https://nelsistech.com/',
    'depends': ['base', 'account'],
    'data': [
        'security/account_budget_security.xml',
        'security/ir.model.access.csv',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
