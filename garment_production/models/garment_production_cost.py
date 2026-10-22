# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentProductionCost(models.Model):
    """Production Cost tracking. Formula: Total Production Cost = Material
    Cost + Labor Cost + Machine Cost + Washing Cost + Finishing Cost +
    Overhead Cost. See Production Management SRS s.52, Planning & MES SRS
    s.47, Shop Floor SRS s.39."""
    _name = 'garment.production.cost'
    _description = 'Garment Production Cost'
    _order = 'create_date desc'

    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    material_cost = fields.Monetary(string='Material Cost', currency_field='currency_id')
    labor_cost = fields.Monetary(string='Labor Cost', currency_field='currency_id')
    machine_cost = fields.Monetary(string='Machine Cost', currency_field='currency_id')
    washing_cost = fields.Monetary(string='Washing Cost', currency_field='currency_id')
    finishing_cost = fields.Monetary(string='Finishing Cost', currency_field='currency_id')
    electricity_cost = fields.Monetary(string='Electricity Cost', currency_field='currency_id')
    maintenance_cost = fields.Monetary(string='Maintenance Cost', currency_field='currency_id')
    overhead_cost = fields.Monetary(string='Overhead Cost', currency_field='currency_id')

    total_cost = fields.Monetary(string='Total Production Cost', compute='_compute_total', store=True,
                                  currency_field='currency_id')
    cost_per_piece = fields.Monetary(string='Cost Per Piece', compute='_compute_total', store=True,
                                      currency_field='currency_id')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('material_cost', 'labor_cost', 'machine_cost', 'washing_cost', 'finishing_cost',
                 'electricity_cost', 'maintenance_cost', 'overhead_cost', 'production_order_id.quantity')
    def _compute_total(self):
        for rec in self:
            rec.total_cost = (rec.material_cost + rec.labor_cost + rec.machine_cost + rec.washing_cost +
                              rec.finishing_cost + rec.electricity_cost + rec.maintenance_cost + rec.overhead_cost)
            qty = rec.production_order_id.quantity
            rec.cost_per_piece = (rec.total_cost / qty) if qty else 0.0
