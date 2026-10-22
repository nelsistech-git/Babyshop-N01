# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentSampleCourier(models.Model):
    """Sample Courier + Submission Management (SRS sections 22-23) —
    garment.sample.courier."""
    _name = 'garment.sample.courier'
    _description = 'Garment Sample Courier'
    _inherit = ['mail.thread']
    _order = 'dispatch_date desc'

    courier_number = fields.Char(string='Courier Number', copy=False, readonly=True, default=lambda s: _('New'))
    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='sample_id.buyer_id', store=True)
    courier_company = fields.Char(string='Courier Company')
    tracking_number = fields.Char(string='Tracking Number')
    dispatch_date = fields.Date(string='Dispatch Date', default=fields.Date.context_today)
    destination_country_id = fields.Many2one('res.country', string='Destination Country')
    buyer_address = fields.Text(string='Buyer Address')
    expected_delivery_date = fields.Date(string='Expected Delivery Date')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By', default=lambda s: s.env.user)
    expected_feedback_date = fields.Date(string='Expected Feedback Date')
    delivery_status = fields.Selection([
        ('prepared', 'Prepared'), ('dispatched', 'Dispatched'), ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'), ('buyer_received', 'Buyer Received'),
    ], string='Delivery Status', default='prepared', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('courier_number', _('New')) == _('New'):
                vals['courier_number'] = self.env['ir.sequence'].next_by_code('garment.sample.courier') or _('New')
        return super().create(vals_list)

    def action_next_status(self):
        flow = ['prepared', 'dispatched', 'in_transit', 'delivered', 'buyer_received']
        for rec in self:
            idx = flow.index(rec.delivery_status)
            if idx < len(flow) - 1:
                rec.delivery_status = flow[idx + 1]
                if rec.delivery_status in ('delivered', 'buyer_received'):
                    rec.sample_id.message_post(
                        body=_('Courier %s: %s.') % (rec.courier_number, rec.delivery_status))
