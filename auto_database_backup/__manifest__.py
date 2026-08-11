# -*- coding: utf-8 -*-

{
    'name': "Automatic Database Backup",
    'summary': 'Generate automatic backup of databases and store to local, '
               'google drive, dropbox, nextcloud, amazon S3, onedrive or '
               'remote server, Odoo17',
    'description': 'automatic database backup, odoo17, odoo apps,backup, automatic backup,odoo17 automatic database backup,backup google drive,backup dropbox, backup nextcloud, backup amazon S3, backup onedrive',

    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'author': 'Nelsis Tech Limited',
    'website': 'https://nelsistech.com/',

    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/db_backup_configure_views.xml',
        'wizard/dropbox_auth_code_views.xml',
    ],
    'external_dependencies': {
        'python': ['dropbox', 'pyncclient', 'boto3', 'nextcloud-api-wrapper','paramiko']},
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
