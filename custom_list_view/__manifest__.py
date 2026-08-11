{
    'name': 'Custom List View',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Helps to Show Row Number, Fixed Header, Duplicate Record, '
               'Highlight Selected Record, Print and Copy Listview items',
    'description': "This module Helps to Show Row Number, Fixed Header, "
                   "Duplicate Record and Highlight Selected Record in List "
                   "View. Using this module the list view items can be printed"
                   " in pdf, excel and csv format, Also there is copy to "
                   "clipboard and pagination features.",
    'author': 'Nelsis Tech Limited',
    'company': 'Nelsis Tech Limited',
    'maintainer': 'Nelsis Tech Limited',
    'website': 'https://nelsistech.com/',
    'depends': ['web', 'account'],
    'data': [
        'report/custom_list_view_templates.xml',
        'report/custom_list_view_reports.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'custom_list_view/static/src/js/list_controller.js',
            'custom_list_view/static/src/js/list_renderer.js',
            'custom_list_view/static/src/xml/list_controller.xml',
            'custom_list_view/static/src/xml/list_renderer.xml',
        ]
    },
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
