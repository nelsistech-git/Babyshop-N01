{
    'name': 'Nelsis Login Theme',
    'summary': 'Fully configurable, brand-matched glassy login page for Odoo Community',
    'description': """
Nelsis Login Theme
===================
Replaces the default Odoo login page with a two-column, glassmorphism-style
design that you fully control from Settings > Login Page Theme, with no code
changes required:

* Upload your own company logo (shown above the login form)
* Set an editable Welcome title and subtitle
* Upload an image, GIF, or video to display beside the login form
* A blurred "glassy" background is generated automatically from a static
  image you choose (kept static even if the side panel shows a video)
* Editable copyright line ("© Company Name ...")
* Editable "Powered by" line with its own optional logo/image
* The default "Not a member? Create an account" link is hidden
* Does not touch Odoo's core login/authentication logic in any way - only
  the visual template is extended, so upgrades stay safe
""",
    'version': '17.0.1.0.3',
    'category': 'Website/Website',
    'author': 'Nelsis Tech',
    'website': 'https://nelsis.tech',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'data/login_theme_default_data.xml',
        'views/login_theme_config_views.xml',
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'nelsis_login_theme/static/src/css/login_theme.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}