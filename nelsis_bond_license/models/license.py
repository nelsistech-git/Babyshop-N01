# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BondWarehouseLicense(models.Model):
    _name = 'bond.warehouse.license'
    _description = 'Bond Warehouse License'
    _inherit = ['bond.warehouse.lifecycle.mixin', 'bond.warehouse.expiry.mixin',
                'bond.warehouse.rule.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date desc, id desc'

    _bond_status_transitions = {
        'suspend': ({'active'}, 'suspended'),
        'reinstate': ({'suspended'}, 'active'),
        'cancel': ({'draft', 'active', 'suspended', 'expired'}, 'cancelled'),
    }
    _bond_expiry_field = 'expiry_date'
    _bond_active_states = ('active',)
    _LOCKED_FIELDS = ('license_number', 'company_id', 'issue_date', 'effective_date', 'license_type_id')

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    license_number = fields.Char(required=True, tracking=True, copy=False)
    license_type_id = fields.Many2one('bond.license.type', string='License Type', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    factory_name = fields.Char(string='Factory', required=True, tracking=True)
    factory_partner_id = fields.Many2one('res.partner', string='Factory Contact / Address')
    factory_category_id = fields.Many2one('bond.factory.category', string='Applicable Factory Category',
                                          required=True, tracking=True)
    issuing_authority = fields.Char(required=True)
    customs_office = fields.Char(string='Customs Office', required=True)
    issue_date = fields.Date(required=True, tracking=True)
    effective_date = fields.Date(required=True, tracking=True)
    expiry_date = fields.Date(required=True, tracking=True)
    location_ids = fields.Many2many('stock.location', 'bond_license_location_rel', 'license_id',
                                    'location_id', string='Authorized Warehouse Locations',
                                    domain="[('usage', '=', 'internal')]")
    responsible_id = fields.Many2one('res.users', string='Responsible Officer',
                                     default=lambda self: self.env.user, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', 'bond_license_attachment_rel', 'license_id',
                                      'attachment_id', string='Supporting Documents')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('suspended', 'Suspended'),
        ('expired', 'Expired'), ('cancelled', 'Cancelled'),
    ], default='draft', required=True, copy=False, tracking=True)

    renewal_ids = fields.One2many('bond.warehouse.license.renewal', 'license_id', string='Renewals')
    security_ids = fields.One2many('bond.warehouse.security', 'license_id', string='Securities')
    entitlement_ids = fields.One2many('bond.warehouse.entitlement', 'license_id', string='Entitlements')
    renewal_count = fields.Integer(compute='_compute_counts')
    security_count = fields.Integer(compute='_compute_counts')
    entitlement_count = fields.Integer(compute='_compute_counts')
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry')
    renewal_status = fields.Selection([
        ('none', 'No Renewal'), ('draft', 'Draft'), ('applied', 'Applied'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], compute='_compute_renewal_status')

    _sql_constraints = [
        ('license_number_company_uniq', 'unique(company_id, license_number)',
         'A license with this number already exists for the company.'),
    ]

    # ------------------------------------------------------------- compute
    @api.depends('name', 'license_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s [%s]' % (rec.name, rec.license_number) if rec.license_number else rec.name

    @api.depends('renewal_ids', 'security_ids', 'entitlement_ids')
    def _compute_counts(self):
        for rec in self:
            rec.renewal_count = len(rec.renewal_ids)
            rec.security_count = len(rec.security_ids)
            rec.entitlement_count = len(rec.entitlement_ids)

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0

    @api.depends('renewal_ids.state')
    def _compute_renewal_status(self):
        for rec in self:
            latest = rec.renewal_ids.sorted('id', reverse=True)[:1]
            rec.renewal_status = latest.state if latest else 'none'

    # --------------------------------------------------------- constraints
    @api.constrains('issue_date', 'effective_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.effective_date and rec.expiry_date and rec.effective_date > rec.expiry_date:
                raise ValidationError(_('The effective date cannot be after the expiry date.'))
            if rec.issue_date and rec.expiry_date and rec.issue_date > rec.expiry_date:
                raise ValidationError(_('The issue date cannot be after the expiry date.'))

    @api.constrains('location_ids')
    def _check_locations(self):
        for rec in self:
            if any(loc.usage != 'internal' for loc in rec.location_ids):
                raise ValidationError(_('Authorized warehouse locations must be internal locations.'))

    # ----------------------------------------------------------------- ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.warehouse.license') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if any(rec.state != 'draft' for rec in self):
            if any(f in vals for f in self._LOCKED_FIELDS):
                raise UserError(_('Identity and date fields are locked once the license leaves draft.'))
            if 'expiry_date' in vals and not self.env.context.get('bond_renewal'):
                raise UserError(_('The expiry date can only be changed through an approved renewal.'))
        return super().write(vals)

    def copy(self, default=None):
        raise UserError(_('Licenses cannot be duplicated. Use the renewal process instead.'))

    def _bond_responsible_user(self):
        self.ensure_one()
        return self.responsible_id or self.create_uid

    # ------------------------------------------------------------ validity
    def _is_valid_on(self, check_date):
        """Public helper for other bond modules: is the license usable on a date?"""
        self.ensure_one()
        return bool(self.state in ('active', 'expired') and self.effective_date and self.expiry_date
                    and self.effective_date <= check_date <= self.expiry_date)

    # ------------------------------------------------------------- actions
    def action_activate(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft licenses can be activated.'))
            if rec.expiry_date < today:
                raise UserError(_('An expired license cannot be activated.'))
            rec._bond_check_rule_verified()
            rec.with_context(bond_status_change=True).write({'state': 'active'})
            rec._log_history('activate', from_state='draft', to_state='active')
        return True

    def action_suspend(self):
        return self._bond_open_wizard('suspend', _('Suspend License'))

    def action_reinstate(self):
        return self._bond_open_wizard('reinstate', _('Reinstate License'))

    def action_cancel(self):
        return self._bond_open_wizard('cancel', _('Cancel License'))

    def _bond_before_transition(self, action_code, target):
        if action_code == 'reinstate' and self.expiry_date < fields.Date.context_today(self):
            return 'expired'
        return target

    def action_new_renewal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Renewal Application'),
            'res_model': 'bond.warehouse.license.renewal', 'view_mode': 'form',
            'context': {'default_license_id': self.id},
        }

    def _action_view(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'tree,form', 'domain': [('license_id', '=', self.id)],
            'context': {'default_license_id': self.id},
        }

    def action_view_renewals(self):
        return self._action_view('bond.warehouse.license.renewal', _('Renewals'))

    def action_view_securities(self):
        return self._action_view('bond.warehouse.security', _('Securities'))

    def action_view_entitlements(self):
        return self._action_view('bond.warehouse.entitlement', _('Entitlements'))
