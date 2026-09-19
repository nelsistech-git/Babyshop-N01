# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models
from odoo.exceptions import UserError


class FwFactory(models.Model):
    _inherit = 'fw.factory'

    raw_material_location_id = fields.Many2one('stock.location', string='Raw Material Zone',
                                                 readonly=True, copy=False)
    wip_location_id = fields.Many2one('stock.location', string='WIP Zone',
                                       readonly=True, copy=False)
    finished_goods_location_id = fields.Many2one('stock.location', string='Finished Goods Zone',
                                                   readonly=True, copy=False)
    zones_configured = fields.Boolean(string='Zones Configured', compute='_compute_zones_configured',
                                       store=True)

    def _compute_zones_configured(self):
        for rec in self:
            rec.zones_configured = bool(
                rec.raw_material_location_id and rec.wip_location_id
                and rec.finished_goods_location_id)

    def action_setup_warehouse_zones(self):
        for rec in self:
            if not rec.warehouse_id:
                raise UserError(
                    "Please link a Warehouse to factory '%s' before setting up zones." % rec.name)
            parent_location = rec.warehouse_id.view_location_id
            Location = self.env['stock.location']
            vals = {}
            if not rec.raw_material_location_id:
                loc = Location.create({
                    'name': 'Raw Material - %s' % rec.name,
                    'location_id': parent_location.id,
                    'usage': 'internal',
                })
                vals['raw_material_location_id'] = loc.id
            if not rec.wip_location_id:
                loc = Location.create({
                    'name': 'WIP - %s' % rec.name,
                    'location_id': parent_location.id,
                    'usage': 'internal',
                })
                vals['wip_location_id'] = loc.id
            if not rec.finished_goods_location_id:
                loc = Location.create({
                    'name': 'Finished Goods - %s' % rec.name,
                    'location_id': parent_location.id,
                    'usage': 'internal',
                })
                vals['finished_goods_location_id'] = loc.id
            if vals:
                rec.write(vals)

    def action_view_zone_stock(self):
        """Open a stock.quant view scoped to this factory's three zones."""
        self.ensure_one()
        location_ids = [loc.id for loc in (
            self.raw_material_location_id, self.wip_location_id,
            self.finished_goods_location_id) if loc]
        if not location_ids:
            raise UserError("Please set up warehouse zones for this factory first.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock by Zone - %s' % self.name,
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('location_id', 'in', location_ids)],
            'context': {'search_default_groupby_location': 1},
        }
