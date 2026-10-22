# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""AI Cost Simulation (SRS section 43): "What happens if fabric price
increases 10%?" — management simulates a % change on material, CM or
overhead cost and sees the resulting FOB, profit impact and required price
adjustment. The simulation is read-only and never writes to the costing
record; "Create Revision from Simulation" opens a pre-filled Cost Revision
for the user to confirm."""

from odoo import api, fields, models, _


class GarmentCostSimulationWizard(models.TransientModel):
    _name = 'garment.cost.simulation.wizard'
    _description = 'Garment AI Cost Simulation'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True)
    currency_id = fields.Many2one('res.currency', related='costing_id.currency_id')

    material_cost_change_pct = fields.Float(string='Material Cost Change (%)',
                                              help='e.g. fabric price increase')
    cm_cost_change_pct = fields.Float(string='CM Cost Change (%)')
    overhead_cost_change_pct = fields.Float(string='Overhead Cost Change (%)')

    current_fob_price = fields.Monetary(string='Current FOB Price', currency_field='currency_id', readonly=True)
    simulated_fob_price = fields.Monetary(string='Simulated FOB Price', currency_field='currency_id', readonly=True)
    profit_impact = fields.Monetary(string='Profit Impact', currency_field='currency_id', readonly=True,
                                     help='Change in profit amount at the current profit margin settings.')
    required_price_adjustment = fields.Monetary(
        string='Required Price Adjustment', currency_field='currency_id', readonly=True,
        help='Increase needed on the FOB price to protect the current profit margin % at the new cost base.')

    @api.onchange('material_cost_change_pct', 'cm_cost_change_pct', 'overhead_cost_change_pct', 'costing_id')
    def _onchange_simulate(self):
        for rec in self:
            costing = rec.costing_id
            if not costing:
                continue
            rec.current_fob_price = costing.fob_price
            new_material = costing.material_cost * (1 + (rec.material_cost_change_pct or 0.0) / 100.0)
            new_cm = costing.cm_cost * (1 + (rec.cm_cost_change_pct or 0.0) / 100.0)
            new_overhead = costing.overhead_cost * (1 + (rec.overhead_cost_change_pct or 0.0) / 100.0)
            new_base = new_material + new_cm + new_overhead + costing.additional_cost_total
            if costing.profit_margin_type == 'fixed':
                new_profit = costing.profit_margin_fixed
            else:
                new_profit = new_base * (costing.profit_margin_pct / 100.0)
            new_fob = new_base + new_profit
            rec.simulated_fob_price = new_fob
            rec.profit_impact = new_profit - costing.profit_amount
            if costing.profit_margin_pct:
                required_fob = new_base * (1 + costing.profit_margin_pct / 100.0)
            else:
                required_fob = new_fob
            rec.required_price_adjustment = required_fob - costing.fob_price

    def action_apply_as_revision(self):
        """Open a New Cost Revision pre-filled with the simulated FOB for the user to confirm and persist."""
        self.ensure_one()
        reason = 'fabric_price_increase' if self.material_cost_change_pct else (
            'production_cost_change' if self.cm_cost_change_pct or self.overhead_cost_change_pct else 'other')
        return {
            'type': 'ir.actions.act_window', 'name': _('New Cost Revision (from Simulation)'),
            'res_model': 'garment.cost.revision', 'view_mode': 'form', 'target': 'new',
            'context': {
                'default_costing_id': self.costing_id.id,
                'default_change_reason': reason,
                'default_previous_fob_price': self.costing_id.fob_price,
                'default_new_fob_price': self.simulated_fob_price,
                'default_change_notes': _(
                    'AI Cost Simulation: material %.1f%%, CM %.1f%%, overhead %.1f%% change.') % (
                    self.material_cost_change_pct, self.cm_cost_change_pct, self.overhead_cost_change_pct),
            },
        }
