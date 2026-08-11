# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Management Review',
    'category': 'Mail',
    'author': 'Kendroo',
    'website': 'https://kendroo.io',
    'description': """
Management review dashboard and reporting tools
=============================
""",
    'version': '17.1',
    'depends': [
        'web',
        'base',
        'base_setup',
        'mail',
        'portal',
        'resource',
        'account',
        'stock',
        'product',
        'sale',
        'purchase',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ssp_review_template_data.xml',
        'data/ssp_data.xml',
        'data/comparison_category_data.xml',
        'data/ir_cron_data.xml',
        'views/ssp_review_dashboard.xml',
        'report/ssp_review_report.xml',
        'views/ssp_views.xml',
        'views/comparison_report_category.xml',
        'views/account_move.xml',
        # 'views/asset_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "management_review/static/src/components/**/*.js",
            "management_review/static/src/components/libs/Chart.bundle.js",
            "management_review/static/src/components/**/*.xml",
            "management_review/static/src/scss/*.scss",
            "management_review/static/src/js/*.js",
            "management_review/static/src/css/style.css",
            # "management_review/static/src/js/libs/Chart.bundle.js",
            # "management_review/static/src/xml/graph_widget.xml",
        ]
    },
    'icon': "/management_review/static/description/icon.png",
    'installable': True,
    'license': 'LGPL-3',
    # 'post_init_hook': '_generate_summary_data',
}
