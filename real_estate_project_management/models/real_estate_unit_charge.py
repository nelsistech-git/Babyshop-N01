# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateUnitCharge(models.Model):
    """Additional pricing charge line on a Property Unit
    (parking, utility, development, registration, service charge,
    floor premium, facing premium, other)."""
    _name = 'real.estate.unit.charge'
    _description = 'Real Estate Unit Additional Charge'
    _rec_name = 'charge_type'
    _order = 'id'

    unit_id = fields.Many2one('real.estate.unit', string='Unit', required=True,
                               ondelete='cascade')
    charge_type = fields.Selection([
        ('parking', 'Parking'),
        ('utility', 'Utility'),
        ('development', 'Development'),
        ('registration', 'Registration'),
        ('service_charge', 'Service Charge'),
        ('floor_premium', 'Floor Premium'),
        ('facing_premium', 'Facing Premium'),
        ('other', 'Other'),
    ], string='Charge Type', required=True, default='other')
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one(related='unit_id.currency_id', readonly=True, store=True)
