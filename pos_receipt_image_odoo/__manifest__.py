# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd.
# See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Receipt Product Image',
    'version': '4.1.3',
    'price': 9.0,
    'category' : 'Sales/Point Of Sale',
    'license': 'Other proprietary',
    'currency': 'EUR',
    'summary': """Show product image on POS receipt.""",
    'description': """
This module allows you show product image on POS receipt.
Show product image on POS receipt
pos receipt image
image product point of sales
pos image product
POS Receipt Product Image
    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/pos_receipt_image_odoo/626',#'https://youtu.be/13FRSlpgx4E',
    'images': [
        'static/description/img.png'
    ],
    'depends': [
        'point_of_sale',
    ],
    'data':[
#        'views/point_of_sale.xml',
    ],
    'assets': {
        # 'point_of_sale.assets': [
        'point_of_sale.assets_prod':[
            'pos_receipt_image_odoo/static/src/js/models.js',
            'pos_receipt_image_odoo/static/src/xml/pos.xml',
        ],
#        'web.assets_qweb': [
#            'pos_receipt_image_odoo/static/src/xml/pos.xml',
#        ],
    },
#    'qweb': [
#        'static/src/xml/pos.xml',
#    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
