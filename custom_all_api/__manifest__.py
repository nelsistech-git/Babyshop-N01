{
    'name': "Custom All API",
    'version': "1.0.0",
    'category': "Others",
    'sequence': 1,
    'summary': "Custom All API for Odoo v17",
    'description': """Custom Mobile API for Odoo v17""",
    'author': "MBH Limited",
    'company': "MBH Limited",
    'maintainer': "MBH Limited",
    'website': '',
    'depends': ['sale_management'],
    'data': [
        'views/inherited_sales_order_views.xml',
    ],

    'installable': True,
    'application': True,
}
