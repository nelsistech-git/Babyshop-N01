# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartnerCustomerLink(models.Model):
    """Phase 5: adds real-estate-specific customer fields directly onto
    res.partner, per the spec's 'reuse res.partner, do not create a
    duplicate customer table' rule (section 33)."""
    _inherit = 'res.partner'

    customer_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('corporate', 'Corporate'),
    ], string='Customer Type')
    nid_passport = fields.Char(string='NID / Passport No.')
    profession = fields.Char(string='Profession')
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')

    booking_ids = fields.One2many('real.estate.booking', 'customer_id', string='Bookings')
    booking_count = fields.Integer(compute='_compute_real_estate_counts')
    sale_agreement_ids = fields.One2many('real.estate.sale.agreement', 'customer_id',
                                          string='Sale Agreements')
    sale_agreement_count = fields.Integer(compute='_compute_real_estate_counts')
    is_real_estate_customer = fields.Boolean(compute='_compute_real_estate_counts', store=True)

    @api.depends('booking_ids', 'sale_agreement_ids')
    def _compute_real_estate_counts(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)
            rec.sale_agreement_count = len(rec.sale_agreement_ids)
            rec.is_real_estate_customer = bool(rec.booking_ids or rec.sale_agreement_ids)

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'res_model': 'real.estate.booking',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }

    def action_view_sale_agreements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Agreements',
            'res_model': 'real.estate.sale.agreement',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
