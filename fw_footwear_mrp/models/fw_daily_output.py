# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo import api


class FwProductionDailyOutput(models.Model):
    _name = 'fw.production.daily.output'
    _description = 'Footwear Daily Production Output Entry'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    stage_line_id = fields.Many2one('fw.production.stage.line', string='Process Stage',
                                     required=True, ondelete='cascade')
    production_order_id = fields.Many2one(related='stage_line_id.production_order_id',
                                           string='Production Order', store=True)
    production_line_id = fields.Many2one(related='stage_line_id.production_line_id',
                                          string='Production Line', store=True)
    stage = fields.Selection(related='stage_line_id.stage', string='Stage', store=True)

    shift = fields.Selection([
        ('day', 'Day Shift'),
        ('night', 'Night Shift'),
        ('general', 'General Shift'),
    ], string='Shift', default='general')

    qty_produced = fields.Integer(string='Qty Produced (Good)', required=True, default=0)
    defect_qty = fields.Integer(string='Defect / Reject Qty', default=0)

    entered_by = fields.Many2one('res.users', string='Entered By',
                                  default=lambda self: self.env.user)
    remarks = fields.Char(string='Remarks')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    @api.constrains('qty_produced', 'defect_qty')
    def _check_quantities(self):
        for rec in self:
            if rec.qty_produced < 0 or rec.defect_qty < 0:
                raise ValidationError("Quantities cannot be negative.")
