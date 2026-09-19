# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwBomVersion(models.Model):
    _name = 'fw.bom.version'
    _description = 'Footwear BOM Version'
    _inherit = ['mail.thread']
    _order = 'style_id, version_no desc'

    name = fields.Char(string='BOM Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.bom.version') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True,
                                ondelete='cascade')
    version_no = fields.Char(string='Version', default='V1', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('obsolete', 'Obsolete'),
    ], string='Status', default='draft', tracking=True)
    date_effective = fields.Date(string='Effective Date', default=fields.Date.context_today)

    line_ids = fields.One2many('fw.bom.line', 'bom_id', string='BOM Components')
    total_cost = fields.Monetary(string='Total Cost per Pair', compute='_compute_total_cost',
                                  store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('style_version_uniq', 'unique(style_id, version_no, company_id)',
         'This BOM version already exists for the selected style!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.bom.version') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.line_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped('line_cost'))

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot confirm a BOM version with no components.")
            # Obsolete any other confirmed BOM for the same style
            other_confirmed = self.search([
                ('style_id', '=', rec.style_id.id),
                ('state', '=', 'confirmed'),
                ('id', '!=', rec.id),
            ])
            other_confirmed.write({'state': 'obsolete'})
        self.write({'state': 'confirmed'})

    def action_set_obsolete(self):
        self.write({'state': 'obsolete'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwBomLine(models.Model):
    _name = 'fw.bom.line'
    _description = 'Footwear BOM Component Line'
    _order = 'sequence, id'

    bom_id = fields.Many2one('fw.bom.version', string='BOM Version',
                              required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    part_name = fields.Char(string='Part', required=True,
                             help="E.g. Upper, Sole, Sock Lining, Lace, Box")
    component_id = fields.Many2one('product.product', string='Component / Material')
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))
    qty_per_pair = fields.Float(string='Qty per Pair', digits='Product Unit of Measure',
                                 default=1.0, required=True)
    wastage_percent = fields.Float(string='Wastage %', default=0.0)
    unit_cost = fields.Float(string='Unit Cost', digits='Product Price')
    line_cost = fields.Monetary(string='Line Cost', compute='_compute_line_cost', store=True,
                                 currency_field='currency_id')
    currency_id = fields.Many2one(related='bom_id.currency_id', string='Currency', store=True)
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty_per_pair', 'wastage_percent', 'unit_cost')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('qty_per_pair', 'Qty per Pair'), ('wastage_percent', 'Wastage %'),
                ('unit_cost', 'Unit Cost'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    @api.onchange('component_id')
    def _onchange_component_id(self):
        if self.component_id:
            self.unit_cost = self.component_id.standard_price
            if self.component_id.uom_id:
                self.uom_id = self.component_id.uom_id

    @api.depends('qty_per_pair', 'wastage_percent', 'unit_cost')
    def _compute_line_cost(self):
        for rec in self:
            effective_qty = rec.qty_per_pair * (1 + (rec.wastage_percent or 0.0) / 100.0)
            rec.line_cost = effective_qty * (rec.unit_cost or 0.0)
