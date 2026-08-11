{
    'name': 'App Collections',
    'summary': 'iOS-style app folder groups with drag-and-drop',
    'version': '17.0.2.0.0',
    'category': 'Tools/UI',
    'license': 'LGPL-3',
    'author': 'Custom',
    'depends': ['muk_web_theme'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'app_collection/static/src/js/app_collection_service.js',
            'app_collection/static/src/js/app_collection_grid.js',
            # Must load after muk_web_theme's navbar.xml so //AppsMenu/DropdownItem exists
            (
                'after',
                'muk_web_theme/static/src/webclient/navbar/navbar.xml',
                'app_collection/static/src/xml/app_collection.xml',
            ),
            'app_collection/static/src/scss/app_collection.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
