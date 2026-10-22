# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentWashingOrder(models.Model):
    """Washing Order — garment washing operations after sewing (Normal,
    Acid, Enzyme, Stone, Bleach, Softener, Special Treatment). See
    Production Management SRS s.41-44."""
    _name = 'garment.washing.order'
    _description = 'Garment Washing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Washing Order Number', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='production_order_id.buyer_id', store=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    quantity = fields.Float(string='Quantity (PCS)', required=True)

    wash_type = fields.Selection([
        ('normal', 'Normal Wash'), ('acid', 'Acid Wash'), ('enzyme', 'Enzyme Wash'),
        ('stone', 'Stone Wash'), ('bleach', 'Bleach Wash'), ('softener', 'Softener Wash'),
        ('special', 'Special Treatment'),
    ], string='Wash Type', required=True)
    recipe_id = fields.Many2one('garment.washing.recipe', string='Recipe',
                                 domain="[('wash_type', '=', wash_type)]")
    machine_id = fields.Many2one('garment.production.machine', string='Machine')

    start_date = fields.Date(string='Start Date')
    completion_date = fields.Date(string='Completion Date')

    chemical_line_ids = fields.One2many('garment.washing.chemical.line', 'washing_order_id', string='Chemical Consumption')

    status = fields.Selection([
        ('draft', 'Draft'), ('garment_received', 'Garment Received'), ('washing', 'Washing In Progress'),
        ('drying', 'Drying'), ('quality_check', 'Quality Inspection'), ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.washing.order') or _('New')
        return super().create(vals_list)

    def action_complete(self):
        self.write({'status': 'completed', 'completion_date': fields.Date.context_today(self)})
