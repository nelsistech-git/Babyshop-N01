# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentProductionTarget(models.Model):
    """Production Target Management — Hourly/Shift/Daily/Monthly targets by
    factory, line, operation or worker. See Planning & MES SRS s.25,
    Advanced MES SRS s.17, Shop Floor SRS s.24."""
    _name = 'garment.production.target'
    _description = 'Garment Production Target'
    _order = 'date desc'

    target_type = fields.Selection([
        ('hourly', 'Hourly Target'), ('shift', 'Shift Target'),
        ('daily', 'Daily Target'), ('monthly', 'Monthly Target'),
    ], string='Target Type', required=True, default='daily')
    target_level = fields.Selection([
        ('factory', 'Factory Target'), ('line', 'Line Target'),
        ('operation', 'Operation Target'), ('worker', 'Worker Target'),
    ], string='Target Level', required=True, default='line')

    line_id = fields.Many2one('garment.production.line', string='Production Line')
    employee_id = fields.Many2one('garment.hr.employee', string='Employee')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    style_id = fields.Many2one('garment.style', string='Style')

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    hour = fields.Selection([(str(h), '%02d:00' % h) for h in range(24)], string='Hour Slot')
    target_qty = fields.Float(string='Target Quantity (PCS)', required=True)
    achieved_qty = fields.Float(string='Achieved Quantity (PCS)', compute='_compute_achieved', store=True)
    achievement_pct = fields.Float(string='Achievement (%)', compute='_compute_achieved', store=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_id', 'date', 'hour', 'target_qty')
    def _compute_achieved(self):
        Entry = self.env['garment.production.entry']
        for rec in self:
            domain = [('date', '=', rec.date)]
            if rec.line_id:
                domain.append(('line_id', '=', rec.line_id.id))
            if rec.hour:
                domain.append(('hour', '=', rec.hour))
            if rec.production_order_id:
                domain.append(('production_order_id', '=', rec.production_order_id.id))
            entries = Entry.search(domain) if rec.line_id or rec.production_order_id else Entry.browse()
            rec.achieved_qty = sum(entries.mapped('output_qty'))
            rec.achievement_pct = (rec.achieved_qty / rec.target_qty * 100.0) if rec.target_qty else 0.0
