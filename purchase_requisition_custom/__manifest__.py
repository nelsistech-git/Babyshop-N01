{
    'name': 'Purchase Requisition Custom',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Custom Purchase Requisition Management with Full Workflow',
    'description': """
        Purchase Requisition Management Module
        =======================================
        - Auto PR Number Generation (PR-YYYY-XXXX)
        - Vendor-based Product Filtering
        - Real-time Inventory Stock Check
        - Full Approval Workflow
        - RFQ / Purchase Order Auto Creation
        - QWeb PDF Report
    """,
    'author': 'Nelsis Tech Limited',
    'website': '',
    'depends': [
        'base',
        'purchase',
        'stock',
        'mail',
        'product',
        'hr',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/purchase_requisition_views.xml',
        'views/purchase_requisition_menu.xml',
        'report/purchase_requisition_report.xml',
        'report/purchase_requisition_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}