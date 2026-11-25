{
    'name': 'Nelsis Field Force - AI Insights',
    'version': '17.0.1.1.0',
    'category': 'Human Resources',
    'summary': 'AI risk engine: detects fake GPS, impossible trips, duplicate bills, abnormal claims and '
               'attendance patterns; daily AI digest (optional Claude API) for administrators.',
    'author': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['nelsis_field_tracking', 'nelsis_field_expense', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/insight_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
}
