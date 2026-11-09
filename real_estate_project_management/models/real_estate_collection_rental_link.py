# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateCollectionRentalLink(models.Model):
    """Phase 7: generalizes real.estate.collection (built in Phase 6 for
    sale installments) to also record rent payments, instead of creating
    a near-duplicate 'Rent Collection' model - per spec item 68's
    'avoid unnecessary database duplication' rule."""
    _inherit = 'real.estate.collection'

    rental_agreement_id = fields.Many2one('real.estate.rental.agreement', string='Rental Agreement',
                                           tracking=True,
                                           domain="[('tenant_id', '=', customer_id)]")
    rent_schedule_id = fields.Many2one('real.estate.rent.schedule', string='Rent Schedule Line',
                                        domain="[('tenant_id', '=', customer_id)]")

    @api.onchange('rent_schedule_id')
    def _onchange_rent_schedule_id(self):
        if self.rent_schedule_id:
            self.amount = self.rent_schedule_id.due_amount
            self.rental_agreement_id = self.rent_schedule_id.rental_agreement_id

    @api.depends('sale_agreement_id', 'sale_agreement_id.project_id', 'sale_agreement_id.unit_id',
                 'rental_agreement_id', 'rental_agreement_id.project_id', 'rental_agreement_id.unit_id')
    def _compute_project_unit(self):
        """Phase 10 bug fix: the Phase 6 compute only looked at
        sale_agreement_id, so rent collections (which only ever set
        rental_agreement_id) never got a project_id/unit_id populated.
        This override widens the same computed fields to also fall back
        to the Rental Agreement, discovered while building the
        Project Profitability report which needed rent collections to
        be attributable to a project."""
        for rec in self:
            if rec.sale_agreement_id:
                rec.project_id = rec.sale_agreement_id.project_id
                rec.unit_id = rec.sale_agreement_id.unit_id
            elif rec.rental_agreement_id:
                rec.project_id = rec.rental_agreement_id.project_id
                rec.unit_id = rec.rental_agreement_id.unit_id
            else:
                rec.project_id = False
                rec.unit_id = False

    def action_confirm(self):
        for rec in self:
            if rec.rent_schedule_id and not rec.allow_overpayment:
                if rec.amount > rec.rent_schedule_id.due_amount + 0.01:
                    raise UserError(
                        'Payment of %.2f exceeds the outstanding amount of %.2f '
                        'on "%s". Enable "Allow Overpayment" to proceed anyway.' % (
                            rec.amount, rec.rent_schedule_id.due_amount,
                            rec.rent_schedule_id.display_name))
        result = super().action_confirm()
        self.mapped('rent_schedule_id')._compute_status_now()
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self.mapped('rent_schedule_id')._compute_status_now()
        return result
