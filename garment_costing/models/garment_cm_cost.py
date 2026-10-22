# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentCmCost(models.Model):
    """Manufacturing Cost / CM (SRS sections 13-15) — garment.cm.cost.
    Supports both a components breakdown and an SMV × Cost-per-Minute
    calculation mode (connects conceptually to a future Industrial
    Engineering module via smv_minutes)."""
    _name = 'garment.cm.cost'
    _description = 'Garment CM (Cost of Making)'
    _order = 'sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    calculation_mode = fields.Selection([
        ('components', 'Cost Components'), ('smv', 'SMV Based'),
    ], string='Calculation Mode', default='components', required=True)

    # Direct Labor
    cutting_cost = fields.Monetary(string='Cutting', currency_field='currency_id')
    sewing_cost = fields.Monetary(string='Sewing', currency_field='currency_id')
    finishing_cost = fields.Monetary(string='Finishing', currency_field='currency_id')
    packing_cost = fields.Monetary(string='Packing', currency_field='currency_id')
    direct_labor_cost = fields.Monetary(string='Direct Labor Total', compute='_compute_total_cm', store=True,
                                         currency_field='currency_id')

    # Machine Cost
    machine_hour_cost = fields.Monetary(string='Machine Hour Cost', currency_field='currency_id')
    maintenance_cost = fields.Monetary(string='Maintenance', currency_field='currency_id')
    depreciation_cost = fields.Monetary(string='Depreciation', currency_field='currency_id')
    machine_cost_total = fields.Monetary(string='Machine Cost Total', compute='_compute_total_cm', store=True,
                                          currency_field='currency_id')

    # Factory Overhead (within CM, distinct from the Costing-level overhead)
    electricity_cost = fields.Monetary(string='Electricity', currency_field='currency_id')
    gas_cost = fields.Monetary(string='Gas', currency_field='currency_id')
    rent_cost = fields.Monetary(string='Rent', currency_field='currency_id')
    admin_cost = fields.Monetary(string='Administration', currency_field='currency_id')
    security_cost = fields.Monetary(string='Security', currency_field='currency_id')
    factory_overhead_total = fields.Monetary(string='Factory Overhead Total', compute='_compute_total_cm',
                                              store=True, currency_field='currency_id')

    # SMV Based
    smv_minutes = fields.Float(string='SMV (Minutes)')
    cost_per_minute = fields.Monetary(string='Cost Per Minute', currency_field='currency_id')

    operation_line_ids = fields.One2many('garment.costing.line', 'cm_cost_id', string='Operation Cost Lines')
    currency_id = fields.Many2one('res.currency', related='costing_id.currency_id', store=True)
    total_cm = fields.Monetary(string='Total CM Cost', compute='_compute_total_cm', store=True,
                                currency_field='currency_id')

    @api.depends('cutting_cost', 'sewing_cost', 'finishing_cost', 'packing_cost',
                 'machine_hour_cost', 'maintenance_cost', 'depreciation_cost',
                 'electricity_cost', 'gas_cost', 'rent_cost', 'admin_cost', 'security_cost',
                 'smv_minutes', 'cost_per_minute', 'calculation_mode', 'operation_line_ids.line_cost')
    def _compute_total_cm(self):
        for rec in self:
            rec.direct_labor_cost = rec.cutting_cost + rec.sewing_cost + rec.finishing_cost + rec.packing_cost
            rec.machine_cost_total = rec.machine_hour_cost + rec.maintenance_cost + rec.depreciation_cost
            rec.factory_overhead_total = (rec.electricity_cost + rec.gas_cost + rec.rent_cost
                                           + rec.admin_cost + rec.security_cost)
            if rec.calculation_mode == 'smv':
                rec.total_cm = (rec.smv_minutes or 0.0) * (rec.cost_per_minute or 0.0)
            elif rec.operation_line_ids:
                rec.total_cm = sum(rec.operation_line_ids.mapped('line_cost'))
            else:
                rec.total_cm = rec.direct_labor_cost + rec.machine_cost_total + rec.factory_overhead_total
