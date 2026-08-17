# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateUnitBookingLink(models.Model):
    """Phase 5: this is the fulfilment of the forward-reference documented
    in real_estate_unit.py since Phase 2 - 'a unit cannot have more than
    one active booking/sale/rental agreement at the same time'. Rental
    will plug into check_single_active_booking() the same way once it
    exists in a later phase, rather than each phase re-implementing the
    check independently."""
    _inherit = 'real.estate.unit'

    booking_ids = fields.One2many('real.estate.booking', 'unit_id', string='Bookings')
    booking_count = fields.Integer(compute='_compute_sales_counts')
    sale_agreement_ids = fields.One2many('real.estate.sale.agreement', 'unit_id',
                                          string='Sale Agreements')
    sale_agreement_count = fields.Integer(compute='_compute_sales_counts')

    @api.depends('booking_ids.state', 'sale_agreement_ids.state')
    def _compute_sales_counts(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)
            rec.sale_agreement_count = len(rec.sale_agreement_ids)

    def check_single_active_booking(self, exclude_booking_id=None, exclude_agreement_id=None):
        """Raise if this unit already has another non-cancelled booking
        or non-cancelled/non-completed sale agreement, other than the one
        (if any) being confirmed/activated right now."""
        self.ensure_one()
        active_bookings = self.booking_ids.filtered(
            lambda b: b.state in ('submitted', 'approved', 'confirmed')
            and b.id != exclude_booking_id)
        active_agreements = self.sale_agreement_ids.filtered(
            lambda a: a.state == 'active' and a.id != exclude_agreement_id)
        if active_bookings or active_agreements:
            raise UserError(
                'Unit "%s" already has an active booking or sale agreement. '
                'A unit cannot have more than one active booking/sale/rental '
                'agreement at the same time.' % self.name)
