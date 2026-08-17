# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartnerWarrantyLink(models.Model):
    _inherit = 'res.partner'

    warranty_ids = fields.One2many('real.estate.warranty', 'customer_id', string='Warranty Claims')
    warranty_count = fields.Integer(compute='_compute_warranty_count')

    @api.depends('warranty_ids.status')
    def _compute_warranty_count(self):
        for rec in self:
            rec.warranty_count = len(rec.warranty_ids)

    def action_view_warranty_claims(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warranty Claims',
            'res_model': 'real.estate.warranty',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
