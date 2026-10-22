# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionRework(models.Model):
    """Production Rework Management: Defect Found -> Rework Order -> Repair
    -> Quality Check -> Release. See Shop Floor SRS s.31."""
    _name = 'garment.production.rework'
    _description = 'Garment Production Rework'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Rework Number', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    bundle_id = fields.Many2one('garment.cutting.bundle', string='Bundle')
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', default='sewing')

    quantity = fields.Float(string='Quantity (PCS)', required=True)
    reason = fields.Char(string='Reason')
    assigned_to_id = fields.Many2one('garment.hr.employee', string='Assigned To')
    rework_date = fields.Date(string='Rework Date', default=fields.Date.context_today)
    completion_date = fields.Date(string='Completion Date')

    status = fields.Selection([
        ('pending', 'Pending'), ('in_repair', 'In Repair'), ('quality_check', 'Quality Check'),
        ('released', 'Released'),
    ], string='Status', default='pending', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.production.rework') or _('New')
        return super().create(vals_list)

    def action_release(self):
        self.write({'status': 'released', 'completion_date': fields.Date.context_today(self)})
