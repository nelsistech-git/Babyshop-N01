# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentWarehouse(models.Model):
    """Warehouse Structure Management (SRS section 5) — garment.warehouse."""
    _name = 'garment.warehouse'
    _description = 'Garment Warehouse'
    _order = 'name'

    name = fields.Char(string='Warehouse Name', required=True)
    code = fields.Char(string='Warehouse Code', required=True)
    warehouse_type = fields.Selection([
        ('raw_material', 'Raw Material Warehouse'), ('accessories', 'Accessories Warehouse'),
        ('chemical', 'Chemical Warehouse'), ('spare_parts', 'Spare Parts Warehouse'),
        ('finished_goods', 'Finished Goods Warehouse'),
    ], string='Warehouse Type', required=True)
    factory = fields.Char(string='Factory')
    address = fields.Char(string='Address')
    manager_id = fields.Many2one('res.users', string='Warehouse Manager')
    capacity = fields.Float(string='Total Capacity')
    capacity_uom = fields.Char(string='Capacity UoM')
    location_ids = fields.One2many('garment.location', 'warehouse_id', string='Locations')
    material_ids = fields.One2many('garment.material', 'default_warehouse_id', string='Default Materials')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # Warehouse KPIs (SRS: Warehouse Dashboard — Space Utilization, Receiving
    # Performance, Pending Receiving, Low Stock Items).
    location_count = fields.Integer(string='Locations', compute='_compute_warehouse_kpis')
    pending_grn_count = fields.Integer(string='Pending GRNs', compute='_compute_warehouse_kpis')
    low_stock_count = fields.Integer(string='Low/Out of Stock Materials', compute='_compute_warehouse_kpis')
    space_utilization_percent = fields.Float(string='Space Utilization %', compute='_compute_warehouse_kpis',
                                              help='Approximate: sum of occupied quantity across bins with a '
                                                   'capacity set, divided by their total capacity. Bins mixing '
                                                   'several materials/UoMs are summed as raw quantity, so treat '
                                                   'this as an operational indicator rather than an exact figure.')

    _sql_constraints = [
        ('warehouse_code_uniq', 'unique(code, company_id)', 'Warehouse Code must be unique per company!'),
    ]

    def _compute_warehouse_kpis(self):
        Grn = self.env['garment.grn']
        for rec in self:
            rec.location_count = len(rec.location_ids)
            rec.pending_grn_count = Grn.search_count([
                ('warehouse_id', '=', rec.id), ('status', '!=', 'completed'),
            ])
            rec.low_stock_count = len(rec.material_ids.filtered(
                lambda m: m.stock_status in ('low_stock', 'out_of_stock')))
            capacity_locs = rec.location_ids.filtered(lambda l: l.capacity)
            total_capacity = sum(capacity_locs.mapped('capacity'))
            total_occupied = sum(capacity_locs.mapped('occupied_qty'))
            rec.space_utilization_percent = (total_occupied / total_capacity * 100.0) if total_capacity else 0.0

    def action_view_pending_grns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending GRNs',
            'res_model': 'garment.grn',
            'view_mode': 'tree,form',
            'domain': [('warehouse_id', '=', self.id), ('status', '!=', 'completed')],
        }

    def action_view_low_stock_materials(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Low/Out of Stock Materials',
            'res_model': 'garment.material',
            'view_mode': 'tree,form',
            'domain': [('default_warehouse_id', '=', self.id), ('stock_status', 'in', ('low_stock', 'out_of_stock'))],
        }

    def action_view_locations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Locations',
            'res_model': 'garment.location',
            'view_mode': 'tree,form',
            'domain': [('warehouse_id', '=', self.id)],
            'context': {'default_warehouse_id': self.id},
        }
