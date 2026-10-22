# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentLineAllocation(models.Model):
    """Line Allocation — assigns a production order/style to a factory line
    for a date range. See Planning & MES SRS s.11 (Line Planning
    Management)."""
    _name = 'garment.line.allocation'
    _description = 'Garment Line Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    plan_id = fields.Many2one('garment.production.plan', string='Production Plan', ondelete='cascade')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    line_id = fields.Many2one('garment.production.line', string='Assigned Line', required=True, tracking=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    planned_qty = fields.Float(string='Planned Quantity (PCS)')

    # Line assignment factors (SRS)
    style_complexity = fields.Selection([
        ('simple', 'Simple'), ('medium', 'Medium'), ('complex', 'Complex'),
    ], string='Style Complexity')
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3))
    delivery_priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Delivery Priority', default='normal')

    status = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('in_progress', 'In Progress'), ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
