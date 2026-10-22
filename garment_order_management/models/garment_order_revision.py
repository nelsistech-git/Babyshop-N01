# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderRevision(models.Model):
    """Order Revision Management (SRS sections 44-45) -
    garment.order.revision. Any major post-confirmation change (quantity,
    style, color, size ratio, shipment date, price) is logged here as an
    audited revision instead of a silent edit.
    """
    _name = 'garment.order.revision'
    _description = 'Garment Order Revision'
    _order = 'order_id, revision_number desc'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')
    revision_number = fields.Integer(string='Revision Number', default=1)

    revision_type = fields.Selection([
        ('quantity_change', 'Quantity Change'),
        ('style_change', 'Style Change'),
        ('color_change', 'Color Change'),
        ('size_ratio_change', 'Size Ratio Change'),
        ('shipment_date_change', 'Shipment Date Change'),
        ('price_change', 'Price Change'),
        ('other', 'Other'),
    ], string='Revision Type', required=True)

    field_changed = fields.Char(string='Field Changed')
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    reason = fields.Text(string='Reason', required=True)

    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft')
    date = fields.Date(string='Date', default=fields.Date.context_today)

    def action_submit(self):
        self.write({'status': 'submitted'})

    def action_approve(self):
        self.write({'status': 'approved', 'approved_by_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'approved_by_id': self.env.user.id})
