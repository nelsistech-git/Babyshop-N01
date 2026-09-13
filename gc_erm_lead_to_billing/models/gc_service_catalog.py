# -*- coding: utf-8 -*-
"""Configurable service master (SRS 8.3) and its categories."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

BILLING_POLICY_SELECTION = [
    ('full', 'Full Billing on Installation'),
    ('advance_final', 'Advance + Final'),
    ('delivery', 'Delivery Based'),
    ('milestone', 'Milestone Based'),
    ('advance', 'Advance (100% before delivery)'),
    ('recurring', 'Recurring (future phase)'),
]

MARGIN_METHOD_SELECTION = [
    ('fixed', 'Fixed Amount'),
    ('cost_pct', 'Percentage on Cost'),
    ('price_pct', 'Percentage on Selling Price'),
]


class GcErmServiceCategory(models.Model):
    _name = 'gc.erm.service.category'
    _description = 'GC ERM Service Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category', required=True, translate=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('gc_service_category_name_uniq', 'unique(name)',
         'A service category with this name already exists.'),
    ]


class GcErmServiceCatalog(models.Model):
    _name = 'gc.erm.service.catalog'
    _description = 'GC ERM Service Catalog'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Service Name', required=True, translate=True,
                       tracking=True)
    code = fields.Char(string='Service Code', required=True, copy=False,
                       tracking=True,
                       help='Short unique code used on documents and reports.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
        help='Leave empty to share the service across all companies.')

    category_id = fields.Many2one(
        'gc.erm.service.category', string='Service Category', tracking=True)
    product_id = fields.Many2one(
        'product.product', string='Linked Product',
        domain="[('type', 'in', ('service', 'consu', 'product'))]",
        help='Odoo product used when this service is pushed to a quotation.')
    uom_id = fields.Many2one(
        'uom.uom', string='Default UoM',
        default=lambda self: self.env.ref('uom.product_uom_unit',
                                          raise_if_not_found=False))
    default_duration = fields.Integer(
        string='Default Duration (months)', default=12,
        help='Default contract duration proposed on leads and proposals.')

    pricing_rule = fields.Selection(
        MARGIN_METHOD_SELECTION, string='Default Pricing Rule',
        default='cost_pct', required=True,
        help='Default margin method applied to BOQ lines for this service.')
    default_margin = fields.Float(
        string='Default Margin', default=20.0,
        help='Fixed amount or percentage, depending on the pricing rule.')

    survey_required = fields.Boolean(
        string='Technical Survey Required', default=True,
        help='If enabled, a lead requesting this service must go through a '
             'technical survey before a proposal can be approved.')
    installation_required = fields.Boolean(
        string='Installation Required', default=True,
        help='If enabled, installation must be completed before final billing.')
    billing_policy = fields.Selection(
        BILLING_POLICY_SELECTION, string='Billing Policy', default='full',
        required=True,
        help='Default billing policy proposed on the work order (SRS 41/43).')

    advance_percent = fields.Float(string='Advance %', default=0.0)
    installation_percent = fields.Float(string='Installation %', default=0.0)
    completion_percent = fields.Float(string='Completion %', default=0.0)

    description = fields.Text(string='Description', translate=True)

    _sql_constraints = [
        ('gc_service_code_uniq', 'unique(code, company_id)',
         'The service code must be unique per company.'),
    ]

    @api.constrains('advance_percent', 'installation_percent',
                    'completion_percent', 'billing_policy')
    def _check_milestone_percentages(self):
        for service in self:
            if service.billing_policy != 'milestone':
                continue
            total = (service.advance_percent + service.installation_percent
                     + service.completion_percent)
            if abs(total - 100.0) > 0.01:
                raise ValidationError(_(
                    "Milestone percentages of service '%(name)s' must add up "
                    "to 100%%. They currently add up to %(total).2f%%.",
                    name=service.name, total=total))

    @api.constrains('default_margin', 'pricing_rule')
    def _check_margin(self):
        for service in self:
            if service.default_margin < 0:
                raise ValidationError(_('The default margin cannot be negative.'))
            if service.pricing_rule == 'price_pct' and service.default_margin >= 100:
                raise ValidationError(_(
                    'A margin expressed as a percentage on selling price must '
                    'be below 100%.'))

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for service in self:
            service.display_name = f'[{service.code}] {service.name}' \
                if service.code else service.name
