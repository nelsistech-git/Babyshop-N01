# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateLand(models.Model):
    """A parcel of land acquired or under negotiation by the company.

    NOTE (Phase 2 forward-reference): a `project_id` Many2one to
    `real.estate.project` will be added by inheritance once the Project
    Management model is introduced in Phase 2, per the phased build plan.
    """
    _name = 'real.estate.land'
    _description = 'Real Estate Land'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Land Number', copy=False, tracking=True,
                        default='New', readonly=True)
    land_name = fields.Char(string='Land Name', required=True, tracking=True)

    ownership_line_ids = fields.One2many(
        'real.estate.land.ownership', 'land_id', string='Land Owners')
    total_ownership_percentage = fields.Float(
        string='Total Ownership %', compute='_compute_total_ownership',
        store=True, digits=(5, 2))

    location = fields.Char(string='Location')
    address = fields.Text(string='Address')
    district = fields.Char(string='District')
    upazila = fields.Char(string='Upazila')

    area = fields.Float(string='Area', digits=(12, 4), tracking=True)
    area_uom = fields.Selection([
        ('sqft', 'Square Feet'),
        ('sqm', 'Square Meter'),
        ('acre', 'Acre'),
        ('bigha', 'Bigha'),
        ('katha', 'Katha'),
        ('decimal', 'Decimal'),
        ('hectare', 'Hectare'),
    ], string='Measurement Unit', default='decimal', required=True)

    deed_number = fields.Char(string='Deed Number')
    khatian_number = fields.Char(string='Khatian Number')
    dag_number = fields.Char(string='Dag Number')
    mouza = fields.Char(string='Mouza')
    jl_number = fields.Char(string='JL Number')
    registration_date = fields.Date(string='Registration Date')

    mutation_status = fields.Selection([
        ('pending', 'Pending'),
        ('applied', 'Applied'),
        ('completed', 'Completed'),
    ], string='Mutation Status', default='pending', tracking=True)

    tax_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], string='Tax Status', default='pending', tracking=True)

    legal_verification = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('verified', 'Verified'),
        ('issues_found', 'Issues Found'),
    ], string='Legal Verification', default='not_started', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_verification', 'Under Verification'),
        ('verified', 'Verified'),
        ('under_agreement', 'Under Agreement'),
        ('allocated', 'Allocated to Project'),
        ('active', 'Active'),
        ('released', 'Released'),
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    agreement_ids = fields.One2many(
        'real.estate.land.agreement', 'land_id', string='Agreements')
    agreement_count = fields.Integer(compute='_compute_agreement_count')

    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_land_ir_attachment_rel',
        'land_id', 'attachment_id', string='Documents',
        help='Attach Deed, Khatian, Mutation, Tax Receipt, NID, Survey, '
             'Legal Documents, Power of Attorney, etc.')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True)

    @api.depends('ownership_line_ids.ownership_percentage')
    def _compute_total_ownership(self):
        for rec in self:
            rec.total_ownership_percentage = sum(
                rec.ownership_line_ids.mapped('ownership_percentage'))

    def _compute_agreement_count(self):
        for rec in self:
            rec.agreement_count = len(rec.agreement_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.land') or 'New'
        return super().create(vals_list)

    def _check_ownership_complete(self):
        for rec in self:
            if rec.ownership_line_ids and \
                    round(rec.total_ownership_percentage, 2) != 100.0:
                raise ValidationError(
                    'Total ownership percentage for land "%s" must equal '
                    '100%% before it can be verified/activated. '
                    'Current total: %.2f%%.' % (
                        rec.land_name, rec.total_ownership_percentage))
            if not rec.ownership_line_ids:
                raise ValidationError(
                    'Land "%s" must have at least one owner with an '
                    'ownership percentage before verification.' % rec.land_name)

    def action_submit_verification(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft land records can be submitted '
                                 'for verification.')
        self.write({'state': 'under_verification'})

    def action_verify(self):
        self._check_ownership_complete()
        for rec in self:
            if rec.state != 'under_verification':
                raise UserError('Only lands under verification can be marked verified.')
        self.write({'state': 'verified', 'legal_verification': 'verified'})

    def action_mark_under_agreement(self):
        self._check_ownership_complete()
        self.write({'state': 'under_agreement'})

    def action_activate(self):
        self._check_ownership_complete()
        self.write({'state': 'active'})

    def action_release(self):
        self.write({'state': 'released'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_view_agreements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Land Agreements',
            'res_model': 'real.estate.land.agreement',
            'view_mode': 'tree,form',
            'domain': [('land_id', '=', self.id)],
            'context': {'default_land_id': self.id},
        }

    @api.constrains('ownership_line_ids')
    def _check_ownership_not_exceeding(self):
        for rec in self:
            total = sum(rec.ownership_line_ids.mapped('ownership_percentage'))
            if round(total, 2) > 100.0:
                raise ValidationError(
                    'Total ownership percentage for land "%s" cannot exceed '
                    '100%% (currently %.2f%%).' % (rec.land_name, total))
