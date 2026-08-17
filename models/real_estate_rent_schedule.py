# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateRentSchedule(models.Model):
    """A single recurring rent-due line under a Rental Agreement.
    Statuses match spec section 44: Paid, Due, Overdue, Partial,
    Cancelled. Paid amount is computed live from confirmed
    real.estate.collection records linked via rent_schedule_id."""
    _name = 'real.estate.rent.schedule'
    _description = 'Real Estate Rent Schedule'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'rental_agreement_id, due_date'

    rental_agreement_id = fields.Many2one('real.estate.rental.agreement', string='Rental Agreement',
                                           required=True, ondelete='cascade')
    tenant_id = fields.Many2one(related='rental_agreement_id.tenant_id', store=True, readonly=True)
    unit_id = fields.Many2one(related='rental_agreement_id.unit_id', store=True, readonly=True)
    project_id = fields.Many2one(related='rental_agreement_id.project_id', store=True, readonly=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    amount = fields.Monetary(string='Amount', required=True)

    collection_ids = fields.One2many('real.estate.collection', 'rent_schedule_id', string='Collections')
    paid_amount = fields.Monetary(string='Paid Amount', compute='_compute_paid_amount', store=True)
    due_amount = fields.Monetary(string='Outstanding', compute='_compute_paid_amount', store=True)

    status = fields.Selection([
        ('due', 'Due'),
        ('overdue', 'Overdue'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='due', required=True, tracking=True)

    company_id = fields.Many2one(related='rental_agreement_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='rental_agreement_id.currency_id', readonly=True)

    @api.depends('rental_agreement_id.name', 'due_date')
    def _compute_display_name(self):
        for rec in self:
            base = rec.rental_agreement_id.name or ''
            rec.display_name = '%s - %s' % (base, rec.due_date) if rec.due_date else base

    @api.depends('collection_ids.amount', 'collection_ids.state', 'amount')
    def _compute_paid_amount(self):
        for rec in self:
            paid = sum(rec.collection_ids.filtered(lambda c: c.state == 'confirmed').mapped('amount'))
            rec.paid_amount = paid
            rec.due_amount = rec.amount - paid

    def _compute_status_now(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.rental_agreement_id.status in ('terminated',):
                new_status = 'cancelled'
            elif rec.due_amount <= 0:
                new_status = 'paid'
            elif rec.paid_amount > 0:
                new_status = 'partial'
            elif rec.due_date and rec.due_date < today:
                new_status = 'overdue'
            else:
                new_status = 'due'
            if new_status != rec.status:
                rec.status = new_status

    @api.model
    def cron_update_all_statuses(self):
        """Scheduled action companion to the Installment cron - refreshes
        rent schedule due/overdue status daily."""
        schedules = self.search([('status', 'not in', ('paid', 'cancelled'))])
        schedules._compute_status_now()
