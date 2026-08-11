{
    'name': 'Change Password',
    'version': '1.0.1',
    'category': 'Change Password',
    'sequence': 1,
    'summary': 'Change Password for Odoo v17',
    'description': """Change Password for Odoo v17""",
    'author': 'Nelsis Tech Limited',
    'company': 'Nelsis Tech Limited',
    'maintainer': 'Nelsis Tech Limited',
    'website': 'https://nelsistech.com/',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/technician_password_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'change_password/static/src/js/hide_extra_menu_and_change_pass.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
    'application': True,
    'auto_install': False,
}
