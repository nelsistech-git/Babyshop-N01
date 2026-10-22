# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionMaterialIssue(models.Model):
    """Material Issue to Production Floor workflow: Production Order ->
    Material Request -> Store Approval -> Material Issue -> Production
    Floor. See Production Management SRS s.16/22, Shop Floor SRS s.14."""
    _name = 'garment.production.material.issue'
    _description = 'Garment Production Material Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    material_id = fields.Many2one('garment.material', string='Material', required=True, tracking=True)
    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse')
    stock_move_id = fields.Many2one('garment.stock.move', string='Stock Move Reference')

    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', required=True, default='cutting')

    requested_qty = fields.Float(string='Requested Quantity', required=True)
    approved_qty = fields.Float(string='Approved Quantity')
    issued_qty = fields.Float(string='Issued Quantity')
    uom = fields.Char(string='UoM')

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    approval_date = fields.Date(string='Store Approval Date')
    issue_date = fields.Date(string='Issue Date')

    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Store Approved By')
    issued_by_id = fields.Many2one('res.users', string='Issued By')

    status = fields.Selection([
        ('requested', 'Requested'), ('store_approved', 'Store Approved'),
        ('issued', 'Issued'), ('rejected', 'Rejected'),
    ], string='Status', default='requested', tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.production.material.issue') or _('New')
        return super().create(vals_list)

    def action_store_approve(self):
        self.write({'status': 'store_approved', 'approval_date': fields.Date.context_today(self),
                    'approved_by_id': self.env.user.id, 'approved_qty': self.requested_qty})

    def action_issue(self):
        self.write({'status': 'issued', 'issue_date': fields.Date.context_today(self),
                    'issued_by_id': self.env.user.id,
                    'issued_qty': self.issued_qty or self.approved_qty or self.requested_qty})

    def action_reject(self):
        self.write({'status': 'rejected'})
