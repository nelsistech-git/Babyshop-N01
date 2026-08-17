# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateProjectSalesLink(models.Model):
    """Phase 5: adds Bookings/Sale Agreements visibility to the Project,
    per spec section 65's 'Project form: ... Sales, Collections' smart
    button list."""
    _inherit = 'real.estate.project'

    booking_ids = fields.One2many('real.estate.booking', 'project_id', string='Bookings')
    booking_count = fields.Integer(compute='_compute_sales_stats')
    sale_agreement_ids = fields.One2many('real.estate.sale.agreement', 'project_id',
                                          string='Sale Agreements')
    sale_agreement_count = fields.Integer(compute='_compute_sales_stats')
    total_sales_value = fields.Monetary(string='Total Sales Value', compute='_compute_sales_stats')

    @api.depends('sale_agreement_ids.net_price', 'sale_agreement_ids.state', 'booking_ids')
    def _compute_sales_stats(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)
            rec.sale_agreement_count = len(rec.sale_agreement_ids)
            active_agreements = rec.sale_agreement_ids.filtered(
                lambda a: a.state in ('active', 'completed'))
            rec.total_sales_value = sum(active_agreements.mapped('net_price'))

    def action_view_project_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'res_model': 'real.estate.booking',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_project_sale_agreements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Agreements',
            'res_model': 'real.estate.sale.agreement',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
