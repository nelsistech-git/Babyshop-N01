# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BondWarehouseSecurity(models.Model):
    _name = 'bond.warehouse.security'
    _description = 'Bond Warehouse General Bond / Security'
    _inherit = ['bond.warehouse.lifecycle.mixin', 'bond.warehouse.expiry.mixin',
                'mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date desc, id desc'

    _bond_status_transitions = {
        'release': ({'active', 'expired'}, 'released'),
        'cancel': ({'draft', 'active'}, 'cancelled'),
        'mark_renewed': ({'active', 'expired'}, 'renewed'),
    }
    _bond_expiry_field = 'expiry_date'
    _bond_active_states = ('active',)

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    instrument_number = fields.Char(tracking=True, copy=False)
    instrument_type = fields.Selection([
        ('bank_guarantee', 'Bank Guarantee'), ('bond', 'Bond'), ('insurance', 'Insurance Guarantee'),
        ('cash', 'Cash Deposit'), ('other', 'Other')], string='Instrument Type', required=True,
        default='bank_guarantee', tracking=True)
    issuer_id = fields.Many2one('res.partner', string='Issuing Bank / Institution', tracking=True)
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', tracking=True)
    license_id = fields.Many2one('bond.warehouse.license', string='License', required=True,
                                 ondelete='restrict', tracking=True)
    company_id = fields.Many2one(related='license_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(currency_field='currency_id', tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible Officer',
                                     default=lambda self: self.env.user)
    attachment_ids = fields.Many2many('ir.attachment', 'bond_security_attachment_rel', 'security_id',
                                      'attachment_id', string='Supporting Documents')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('renewed', 'Renewed'),
        ('released', 'Released'), ('cancelled', 'Cancelled'),
    ], default='draft', required=True, copy=False, tracking=True)
    renewed_from_id = fields.Many2one('bond.warehouse.security', string='Renewal Of', copy=False,
                                      readonly=True)
    renewed_by_ids = fields.One2many('bond.warehouse.security', 'renewed_from_id', string='Renewed By')
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry')

    _sql_constraints = [
        ('instrument_issuer_uniq', 'unique(instrument_number, issuer_id)',
         'This instrument number already exists for the issuing institution.'),
    ]

    @api.depends('name', 'instrument_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s [%s]' % (rec.name, rec.instrument_number) if rec.instrument_number else rec.name

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0

    @api.constrains('amount', 'issue_date', 'expiry_date')
    def _check_values(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_('The amount cannot be negative.'))
            if rec.issue_date and rec.expiry_date and rec.issue_date > rec.expiry_date:
                raise ValidationError(_('The issue date cannot be after the expiry date.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.warehouse.security') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        locked = ('instrument_number', 'issuer_id', 'amount', 'currency_id', 'issue_date',
                  'expiry_date', 'license_id', 'beneficiary_id', 'instrument_type')
        if any(f in vals for f in locked) and any(rec.state != 'draft' for rec in self):
            raise UserError(_('Instrument details are locked once the record leaves draft. '
                              'Use the renewal action to record a new instrument.'))
        return super().write(vals)

    def _bond_responsible_user(self):
        self.ensure_one()
        return self.responsible_id or self.create_uid

    def action_activate(self):
        today = fields.Date.context_today(self)
        required = (('instrument_number', _('Instrument Number')), ('issuer_id', _('Issuing Institution')),
                    ('beneficiary_id', _('Beneficiary')), ('amount', _('Amount')),
                    ('issue_date', _('Issue Date')), ('expiry_date', _('Expiry Date')))
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft instruments can be activated.'))
            missing = [label for fname, label in required if not rec[fname]]
            if missing:
                raise UserError(_('Missing required values: %s', ', '.join(missing)))
            if rec.license_id.state == 'cancelled':
                raise UserError(_('The linked license is cancelled.'))
            if rec.expiry_date < today:
                raise UserError(_('An expired instrument cannot be activated.'))
            rec.with_context(bond_status_change=True).write({'state': 'active'})
            rec._log_history('activate', from_state='draft', to_state='active')
            previous = rec.renewed_from_id
            if previous and previous.state in ('active', 'expired'):
                previous._bond_apply_status('mark_renewed', _('Replaced by %s', rec.name))
        return True

    def action_renew(self):
        self.ensure_one()
        if self.state not in ('active', 'expired'):
            raise UserError(_('Only active or expired instruments can be renewed.'))
        new = self.copy({'instrument_number': False, 'issue_date': False, 'expiry_date': False,
                         'renewed_from_id': self.id})
        self._log_history('renew', _('Renewal draft %s created.', new.name))
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': new.id,
                'view_mode': 'form'}

    def action_release(self):
        return self._bond_open_wizard('release', _('Release Instrument'))

    def action_cancel(self):
        return self._bond_open_wizard('cancel', _('Cancel Instrument'))
