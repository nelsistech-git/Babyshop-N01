# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderDelay(models.Model):
    """Order Delay & Recovery Planning (SRS sections 32-33) -
    garment.order.delay.
    """
    _name = 'garment.order.delay'
    _description = 'Garment Order Delay'
    _order = 'order_id, start_date desc, id desc'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')

    delay_department = fields.Char(string='Delay Department', help='e.g. Sewing, Cutting, Finishing, Dyeing.')
    delay_reason = fields.Selection([
        ('buyer_approval', 'Buyer Approval'),
        ('fabric_delay', 'Fabric Delay'),
        ('trim_delay', 'Trim Delay'),
        ('production_delay', 'Production Delay'),
        ('quality_failure', 'Quality Failure'),
        ('shipment_problem', 'Shipment Problem'),
        ('other', 'Other'),
    ], string='Delay Reason', required=True)

    delay_days = fields.Integer(string='Delay Days')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    expected_recovery_date = fields.Date(string='Expected Recovery Date')
    recovery_plan = fields.Text(string='Recovery Plan',
                                 help='e.g. Increase Line Capacity, Add Overtime, Move Production.')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'),
    ], string='Status', default='open')
