# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderApproval(models.Model):
    """Order Approval Workflow (SRS section 15) - garment.order.approval.

    Before production: Order Received -> Merchandising Review ->
    Cost Verification -> Planning Review -> Management Approval ->
    Released For Production.
    """
    _name = 'garment.order.approval'
    _description = 'Garment Order Approval Stage'
    _order = 'order_id, id'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')

    stage = fields.Selection([
        ('order_received', 'Order Received'),
        ('merchandising_review', 'Merchandising Review'),
        ('cost_verification', 'Cost Verification'),
        ('planning_review', 'Planning Review'),
        ('management_approval', 'Management Approval'),
        ('released_for_production', 'Released For Production'),
    ], string='Approval Stage', required=True)

    approver_id = fields.Many2one('res.users', string='Approver', default=lambda s: s.env.user)
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    remarks = fields.Text(string='Remarks')
