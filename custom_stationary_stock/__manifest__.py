{
    'name': 'Custom Stationary Stock',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Stationary Stock Management for BlueDream',
    'description': """
        Adds Stationary Location feature to Inventory & Warehouse.
        - Boolean field on stock.location to mark as stationary location
        - Stationary Stock menu under HR-Employees > Reporting
    """,
    'author': 'Nelsis Limited',
    'company': 'Nelsis Limited',
    'website': '',
    'depends': ['stock', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_location_views.xml',
        'views/stationary_stock_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
