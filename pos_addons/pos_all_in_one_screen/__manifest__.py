# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name"              :  "Pos Advanced Screen",
    "summary"           :  "Upgrade Your Business with Odoo POS Advance Screen: Streamline operations, improve communication, and enhance customer experiences. Enjoy efficient order management, real-time updates, and customizable branding. Benefit from location independence, automated feedback collection, and data-driven decisions. Pos Kitchen Screen|Pos Customer Screen|Pos Cart Screen|Pos Display|Kitchen order management|POS Advance Screen|Odoo Kitchen-Cart-Review Screens|Pos Customer CartPos Customer Display|Pos Multi Screen Display|Pos Multiple Display",
    "category"          :  "Point Of Sale",
    "version"           :  "1.0.0",
    "author"            :  "Webkul Software Pvt. Ltd.",
    "license"           :  "Other proprietary",
    "website"           :  "https://store.webkul.com",
    "description"       :  """Elevate your business with Odoo POS Advance Screen. Streamline operations, enhance communication, and delight customers with efficient features.
                          Kitchen order management
                          Odoo POS Advance Screen
                          POS Advance Screen
                          Advanced Screen
                          Kitchen Screen
                          Cart Screen
                          Review Screen
                          Odoo Kitchen-Cart-Review Screens
                          Customer Feedback,
                          Customer screen in Odoo
                          Review screen in Odoo
                          Kitchen screen in Odoo
    """,
    "live_test_url"     :  "https://odoodemo.webkul.com/?module=pos_all_in_one_screen&custom_url=/pos/auto",
    "depends"           :  ['pos_restaurant'],
    "data"              :  [
                            'security/ir.model.access.csv',
                            'views/pos_cart_screen.xml',
                            'views/pos_kitchen_screen.xml',
                            'views/pos_review_screen.xml',
                            'views/pos_kitchen_screen_views.xml',
                            'views/pos_screen_session.xml',
                            'wizard/pos_close_screen_session_wizard.xml',
                        ],
    "demo"              :  ['data/demo.xml'],
    "assets"            :  {
                            'point_of_sale._assets_pos': [ 
                                'pos_all_in_one_screen/static/src/css/**/*',
                                'pos_all_in_one_screen/static/src/js/**/*',
                                'pos_all_in_one_screen/static/src/xml/pos.xml'
                            ],
                            'web.assets_frontend': [
                                'pos_all_in_one_screen/static/src/css/**/*',
                                'pos_all_in_one_screen/static/src/widgets/**/*',
                                'pos_all_in_one_screen/static/src/js/sweetalert.min.js',
                                'pos_all_in_one_screen/static/src/xml/pos_kitchen_templates.xml',
                                'pos_all_in_one_screen/static/src/xml/pos_screen_templates.xml'
                            ]
                        },
    "images"            :  ['static/description/Banner.png'],
    "application"       :  True,
    "installable"       :  True,
    "auto_install"      :  False,
    "price"             :  299,
    "currency"          :  "USD",
    "pre_init_hook"     :  "pre_init_check",
}
