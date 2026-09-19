# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo import api


class FwWorkerOutput(models.Model):
    _name = 'fw.worker.output'
    _description = 'Footwear Individual Worker Daily Output'
    _order = 'date desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    operation_id = fields.Many2one('fw.operation', string='Operation', required=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line')

    qty_produced = fields.Integer(string='Qty Produced (Good)', required=True, default=0)
    defect_qty = fields.Integer(string='Defect Qty', default=0)

    remarks = fields.Char(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    @api.constrains('qty_produced', 'defect_qty')
    def _check_quantities(self):
        for rec in self:
            if rec.qty_produced < 0 or rec.defect_qty < 0:
                raise ValidationError("Quantities cannot be negative.")
