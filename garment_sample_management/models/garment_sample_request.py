# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentSampleRequest(models.Model):
    """Sample Request Management (SRS section 8) — garment.sample.request."""
    _name = 'garment.sample.request'
    _description = 'Garment Sample Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    request_number = fields.Char(string='Request Number', copy=False, readonly=True, default=lambda s: _('New'))
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    source = fields.Selection([
        ('buyer', 'Buyer'), ('merchandiser', 'Merchandiser'), ('sales_order', 'Sales Order'),
        ('style_development', 'Style Development'), ('tech_pack', 'Tech Pack'),
    ], string='Requested From', default='merchandiser', required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, index=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True, index=True)
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', domain="[('style_id', '=', style_id)]")
    sample_type_id = fields.Many2one('garment.sample.type', string='Sample Type', required=True)
    quantity = fields.Integer(string='Quantity', default=1)
    required_date = fields.Date(string='Required Date')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Critical'),
    ], string='Priority', default='1')
    requester_id = fields.Many2one('res.users', string='Requester', default=lambda s: s.env.user)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)
    sample_id = fields.Many2one('garment.sample', string='Resulting Sample', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('request_number', _('New')) == _('New'):
                vals['request_number'] = self.env['ir.sequence'].next_by_code('garment.sample.request') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        self.write({'approval_status': 'approved'})

    def action_reject(self):
        self.write({'approval_status': 'rejected'})

    def action_create_sample(self):
        self.ensure_one()
        sample = self.env['garment.sample'].create({
            'style_id': self.style_id.id,
            'buyer_id': self.buyer_id.id,
            'sample_type_id': self.sample_type_id.id,
            'techpack_id': self.techpack_id.id,
            'required_date': self.required_date,
            'priority': self.priority,
            'sample_request_id': self.id,
        })
        self.write({'sample_id': sample.id})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'garment.sample',
            'res_id': sample.id, 'view_mode': 'form',
        }
