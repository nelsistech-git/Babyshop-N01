# -*- coding: utf-8 -*-
"""Customer master extensions (SRS 8.1)."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CUSTOMER_TYPE_SELECTION = [
    ('corporate', 'Corporate'),
    ('sme', 'SME'),
    ('government', 'Government'),
    ('ngo', 'NGO'),
    ('individual', 'Individual'),
    ('reseller', 'Reseller / Partner'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gc_district = fields.Char(string='District')
    gc_area = fields.Char(string='Area')
    gc_latitude = fields.Float(string='GPS Latitude', digits=(10, 7))
    gc_longitude = fields.Float(string='GPS Longitude', digits=(10, 7))
    gc_customer_type = fields.Selection(
        CUSTOMER_TYPE_SELECTION, string='Customer Type', index=True)
    gc_map_url = fields.Char(string='Map Link', compute='_compute_gc_map_url')

    gc_lead_ids = fields.One2many('gc.erm.lead', 'partner_id', string='ERM Leads')
    gc_lead_count = fields.Integer(compute='_compute_gc_counts')
    gc_work_order_count = fields.Integer(compute='_compute_gc_counts')
    gc_installation_count = fields.Integer(compute='_compute_gc_counts')

    @api.depends('gc_latitude', 'gc_longitude')
    def _compute_gc_map_url(self):
        for partner in self:
            if partner.gc_latitude or partner.gc_longitude:
                partner.gc_map_url = (
                    'https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s'
                    % (partner.gc_latitude, partner.gc_longitude,
                       partner.gc_latitude, partner.gc_longitude))
            else:
                partner.gc_map_url = False

    def _compute_gc_counts(self):
        Lead = self.env['gc.erm.lead']
        WorkOrder = self.env['gc.erm.work.order']
        Installation = self.env['gc.erm.installation']
        for partner in self:
            partner.gc_lead_count = Lead.search_count(
                [('partner_id', '=', partner.id)])
            partner.gc_work_order_count = WorkOrder.search_count(
                [('partner_id', '=', partner.id)])
            partner.gc_installation_count = Installation.search_count(
                [('partner_id', '=', partner.id)])

    @api.constrains('gc_latitude', 'gc_longitude')
    def _check_gc_gps(self):
        for partner in self:
            if partner.gc_latitude and not -90.0 <= partner.gc_latitude <= 90.0:
                raise ValidationError(_(
                    'GPS latitude must be between -90 and 90 degrees.'))
            if partner.gc_longitude and \
                    not -180.0 <= partner.gc_longitude <= 180.0:
                raise ValidationError(_(
                    'GPS longitude must be between -180 and 180 degrees.'))

    def action_gc_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('ERM Leads'),
            'res_model': 'gc.erm.lead', 'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_gc_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Work Orders'),
            'res_model': 'gc.erm.work.order', 'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_gc_view_installations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Installations'),
            'res_model': 'gc.erm.installation', 'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }
