# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwFactory(models.Model):
    _inherit = 'fw.factory'

    relationship_type = fields.Selection([
        ('owned', 'Owned (In-House)'),
        ('subcontractor', 'Subcontractor (CMT)'),
        ('external_vendor', 'External Vendor (Buy Finished Goods)'),
    ], string='Relationship Type', default='owned', required=True,
        help="Owned: your own production facility, tracked through FW Advanced "
             "Manufacturing as usual.\n"
             "Subcontractor (CMT): a Cut-Make-Trim partner. Order Allocation lines "
             "assigned here can generate a Subcontract Order to track material sent "
             "out and finished goods received back.\n"
             "External Vendor: a third party you simply buy finished goods from, "
             "with no process tracking.")

    subcontractor_contact_id = fields.Many2one(
        'res.partner', string='Subcontractor / Vendor Contact',
        help="Business contact details for a Subcontractor or External Vendor factory.")

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    default_conversion_rate = fields.Monetary(
        string='Default CMT Rate (per Pair)', currency_field='currency_id',
        help="Default Cut-Make-Trim conversion fee per pair for this subcontractor, "
             "used as a starting value when creating Subcontract Orders.")
