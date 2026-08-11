# -*- coding: utf-8 -*-
{
    'name': 'Custom CRM Report',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'CRM Custom Report with Wizard',
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_inherit_view.xml',
        'views/crm_report_wizard_view.xml',
        'report/crm_report_template.xml',
        'report/crm_report_action.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
