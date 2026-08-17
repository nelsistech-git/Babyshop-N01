# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateUnitRentalLink(models.Model):
    """Phase 7: extends the single-active-booking guard (created in
    Phase 5) so a unit cannot be simultaneously sold and rented either."""
    _inherit = 'real.estate.unit'

    rental_agreement_ids = fields.One2many('real.estate.rental.agreement', 'unit_id',
                                            string='Rental Agreements')
    rental_agreement_count = fields.Integer(compute='_compute_rental_stats')

    @api.depends('rental_agreement_ids.status')
    def _compute_rental_stats(self):
        for rec in self:
            rec.rental_agreement_count = len(rec.rental_agreement_ids)

    def check_single_active_booking(self, exclude_booking_id=None, exclude_agreement_id=None,
                                     exclude_rental_id=None):
        self.ensure_one()
        super().check_single_active_booking(exclude_booking_id=exclude_booking_id,
                                             exclude_agreement_id=exclude_agreement_id)
        active_rentals = self.rental_agreement_ids.filtered(
            lambda r: r.status in ('confirmed', 'active') and r.id != exclude_rental_id)
        if active_rentals:
            raise UserError(
                'Unit "%s" already has an active rental agreement. A unit cannot '
                'have more than one active booking/sale/rental agreement at the '
                'same time.' % self.name)
