{
    'name': 'Generate Barcode',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Generate product barcode labels for BabyShop',
    'author': 'Nelsis Tech Limited',
    'depends': ['stock', 'product', 'custom_product_common'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/barcode_label_wizard.xml',
        'report/barcode_label_report.xml',
        'report/barcode_label_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
