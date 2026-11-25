{
    'name': 'Nelsis Field Force - Demo Data',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Realistic demo data for Nelsis Field Force: employees, 14 days of attendance and GPS tracks around '
               'Dhaka (with fake-GPS / offline / clock cases), TA/DA claims with scanned bills, advances, '
               'announcements and AI findings. Install = demo ready; uninstall = demo gone.',
    'author': 'Nelsis Tech',
    'license': 'LGPL-3',
    # only the core module is required; TA/DA, advances and AI demo parts appear when those modules are installed
    'depends': ['nelsis_field_tracking'],
    'data': [
        'views/demo_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
