# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Print Report - Point of Sale Order",
    'price': 20.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': """This module will Print Point of Sale Order in PDF format.""",
    'description': """
This module will Print Point of Sale Order
This module will Print Point of Sale Order in PDF format.
Print POS Order
Print Point of Sale Order PDF
POS Order PDF Report
Point of Sale Order PDF
Print Report - Point of Sale Order
POS Order Send By Email
Send Email POS Orders
print pos
pos
point of sale
pos report
order report
pos sale report
pos order send by email
send by email
pos send by email
send email
order send by email
    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/image.jpg'],
    # 'live_test_url': 'https://youtu.be/80ZgDyk595Q',
    'live_test_url' : 'https://probuseappdemo.com/probuse_apps/pos_order_report/372',#'https://youtu.be/2zaa39aoqbs',
    'version': '7.5',
    'category' : 'Sales/Point of Sale',
    'depends': ['point_of_sale'],
    'data':[
            
            'views/pos_order_view.xml',
            'views/report_reg.xml',
            'views/report_pos_order.xml',
            # 'data/mail_template_data.xml',
            'data/mail_template_data_new.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
