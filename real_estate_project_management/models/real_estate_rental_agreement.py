# -*- coding: utf-8 -*-
import calendar
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateRentalAgreement(models.Model):
    """A rental agreement for a unit. Reuses res.partner for the tenant
    (no duplicate contact data) and plugs into the same
    check_single_active_booking() guard that Sale Agreements use, so a
    unit can never be simultaneously sold and rented."""
    _name = 'real.estate.rental.agreement'
    _description = 'Real Estate Rental Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Rental Agreement Number', copy=False, tracking=True,
                        default='New', readonly=True)
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True,
                                 tracking=True, ondelete='restrict')
    unit_id = fields.Many2one('real.estate.unit', string='Unit', required=True,
                               tracking=True, ondelete='restrict')
    project_id = fields.Many2one(related='unit_id.project_id', store=True, readonly=True)

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)

    monthly_rent = fields.Monetary(string='Monthly Rent', required=True, tracking=True)
    security_deposit = fields.Monetary(string='Security Deposit')
    service_charge = fields.Monetary(string='Service Charge')
    utility_charge = fields.Monetary(string='Utility Charge')
    monthly_total = fields.Monetary(string='Monthly Total (Rent+Charges)', compute='_compute_monthly_total')

    payment_day = fields.Integer(string='Payment Day of Month', default=1,
                                  help='Day of the month rent is due (1-31, clamped to shorter months).')
    renewal_terms = fields.Text(string='Renewal Terms')

    rent_schedule_ids = fields.One2many('real.estate.rent.schedule', 'rental_agreement_id',
                                         string='Rent Schedule')
    rent_schedule_count = fields.Integer(compute='_compute_rent_stats')
    total_collected = fields.Monetary(string='Total Collected', compute='_compute_rent_stats')
    total_outstanding = fields.Monetary(string='Total Outstanding', compute='_compute_rent_stats')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='unit_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('monthly_rent', 'service_charge', 'utility_charge')
    def _compute_monthly_total(self):
        for rec in self:
            rec.monthly_total = rec.monthly_rent + rec.service_charge + rec.utility_charge

    @api.depends('rent_schedule_ids.paid_amount', 'rent_schedule_ids.due_amount')
    def _compute_rent_stats(self):
        for rec in self:
            rec.rent_schedule_count = len(rec.rent_schedule_ids)
            rec.total_collected = sum(rec.rent_schedule_ids.mapped('paid_amount'))
            rec.total_outstanding = sum(rec.rent_schedule_ids.mapped('due_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.rental.agreement') or 'New'
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError('End Date cannot be before Start Date for '
                                       'rental agreement "%s".' % rec.name)

    @api.constrains('payment_day')
    def _check_payment_day(self):
        for rec in self:
            if not (1 <= rec.payment_day <= 31):
                raise ValidationError('Payment Day must be between 1 and 31.')

    def action_confirm(self):
        for rec in self:
            if rec.status != 'draft':
                raise UserError('Only draft rental agreements can be confirmed.')
        self.write({'status': 'confirmed'})

    def action_activate(self):
        for rec in self:
            if rec.status != 'confirmed':
                raise UserError('Only confirmed rental agreements can be activated.')
            rec.unit_id.check_single_active_booking(exclude_rental_id=rec.id)
        self.write({'status': 'active'})
        for rec in self:
            rec.unit_id.write({'status': 'rented'})

    def action_expire(self):
        for rec in self:
            if rec.status != 'active':
                raise UserError('Only active rental agreements can expire.')
        self.write({'status': 'expired'})
        for rec in self:
            if rec.unit_id.status == 'rented':
                rec.unit_id.write({'status': 'available'})

    def action_renew(self):
        """Create a follow-on agreement for the same tenant/unit and mark
        this one Renewed - keeping full history rather than mutating
        this record's dates in place."""
        self.ensure_one()
        if self.status not in ('active', 'expired'):
            raise UserError('Only active or expired rental agreements can be renewed.')
        new_start = self.end_date or fields.Date.context_today(self)
        new_agreement = self.copy({
            'tenant_id': self.tenant_id.id,
            'unit_id': self.unit_id.id,
            'start_date': new_start,
            'end_date': False,
            'status': 'draft',
        })
        self.write({'status': 'renewed'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renewed Rental Agreement',
            'res_model': 'real.estate.rental.agreement',
            'view_mode': 'form',
            'res_id': new_agreement.id,
        }

    def action_terminate(self):
        for rec in self:
            if rec.status not in ('confirmed', 'active'):
                raise UserError('Only confirmed or active rental agreements can be terminated.')
        self.write({'status': 'terminated'})
        for rec in self:
            if rec.unit_id.status == 'rented':
                rec.unit_id.write({'status': 'available'})

    def action_generate_rent_schedule(self):
        for rec in self:
            if rec.rent_schedule_ids:
                raise UserError('This rental agreement already has rent schedule lines.')
            if not (rec.start_date and rec.end_date):
                raise UserError('Set both Start Date and End Date before generating the schedule.')
            lines = []
            cursor = rec.start_date.replace(day=1)
            while cursor <= rec.end_date:
                last_day = calendar.monthrange(cursor.year, cursor.month)[1]
                due_day = min(rec.payment_day or 1, last_day)
                due_date = cursor.replace(day=due_day)
                lines.append((0, 0, {
                    'due_date': due_date,
                    'amount': rec.monthly_total,
                    'status': 'due',
                }))
                cursor = cursor + relativedelta(months=1)
            rec.rent_schedule_ids = lines
