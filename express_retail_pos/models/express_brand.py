# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ExpressPosBrand(models.Model):
    _name = 'express.pos.brand'
    _description = 'Retail Brand'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help='Short code used as a prefix, e.g. BS for Baby Shop, SNS for SNS.')
    logo = fields.Binary(attachment=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    sequence_id = fields.Many2one(
        'ir.sequence', string='Dedicated Numbering Sequence',
        help='Optional: use a separate order/invoice numbering sequence for this brand.')
    branch_ids = fields.One2many('express.pos.branch', 'brand_id', string='Showrooms/Branches')
    product_category_ids = fields.Many2many('product.category', string='Product Categories')
    note = fields.Text()

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Brand code must be unique per company.'),
    ]


class ExpressPosBranch(models.Model):
    _name = 'express.pos.branch'
    _description = 'Showroom / Branch'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    brand_id = fields.Many2one('express.pos.brand', required=True, ondelete='cascade')
    manager_id = fields.Many2one('res.users', string='Branch Manager')
    warehouse_id = fields.Many2one('stock.warehouse')
    address = fields.Text()
    phone = fields.Char(string='Branch Phone', help='Printed on the thermal receipt header. '
                         'Falls back to the company phone when left empty.')
    active = fields.Boolean(default=True)
    receipt_format = fields.Selection([
        ('bd', 'Bangladesh (BDT, non-VAT retail receipt)'),
        ('dubai', 'Dubai / UAE (AED, VAT Tax Invoice)'),
    ], string='Receipt Format', help='Which billing/receipt layout the Checkout Console and the '
       '"Print Receipt" action should use for orders sold from this branch. Leave empty to use '
       'the company-wide default set in Settings > Express Retail Sales.')
    company_id = fields.Many2one('res.company', related='brand_id.company_id', store=True)
    user_ids = fields.Many2many(
        'res.users', 'express_pos_branch_users_rel', 'branch_id', 'user_id',
        string='Cashiers / Staff',
        help='Users allowed to open the Checkout Console for this branch and to see its '
             'sales. Used by the Express POS branch-scoping security rules.')
    default_journal_id = fields.Many2one(
        'account.journal', string='Default Cash Journal', domain=[('type', 'in', ['cash', 'bank'])],
        help='Pre-selected as the first tender in the Payment dialog for this branch.')
    color = fields.Char(string='Theme Color', default='#1f5c3d',
                         help='Accent color shown in the Checkout Console header for this branch.')

    def name_get(self):
        result = []
        for rec in self:
            name = f'{rec.brand_id.name} - {rec.name}' if rec.brand_id else rec.name
            result.append((rec.id, name))
        return result
