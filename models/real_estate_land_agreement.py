# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateLandAgreement(models.Model):
    """Legal agreement between the company and one or more land owners.

    NOTE (Phase 2 forward-reference): a `project_id` Many2one to
    `real.estate.project` will be added by inheritance in Phase 2.
    """
    _name = 'real.estate.land.agreement'
    _description = 'Real Estate Land Owner Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Agreement Number', copy=False, tracking=True,
                        default='New', readonly=True)
    agreement_type = fields.Selection([
        ('joint_venture', 'Joint Venture'),
        ('land_purchase', 'Land Purchase'),
        ('land_lease', 'Land Lease'),
        ('development_agreement', 'Development Agreement'),
        ('revenue_sharing', 'Revenue Sharing'),
        ('flat_sharing', 'Flat Sharing'),
        ('power_of_attorney', 'Power of Attorney'),
        ('other', 'Other'),
    ], string='Agreement Type', required=True, default='joint_venture', tracking=True)

    agreement_date = fields.Date(string='Agreement Date', tracking=True,
                                  default=fields.Date.context_today)
    land_id = fields.Many2one('real.estate.land', string='Land', required=True,
                               tracking=True, ondelete='restrict')
    land_owner_ids = fields.Many2many(
        'real.estate.land.owner', 'real_estate_land_agreement_owner_rel',
        'agreement_id', 'owner_id', string='Land Owners')

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    total_land_area = fields.Float(related='land_id.area', string='Total Land Area',
                                    readonly=True, store=False)

    developer_share_percentage = fields.Float(string='Developer Share (%)', digits=(5, 2))
    land_owner_share_percentage = fields.Float(string='Land Owner Share (%)', digits=(5, 2))

    cash_consideration = fields.Monetary(string='Cash Consideration')
    flat_unit_consideration = fields.Text(string='Flat/Unit Consideration')
    revenue_sharing_notes = fields.Text(string='Revenue Sharing Terms')
    registration_cost = fields.Monetary(string='Registration Cost')
    development_cost = fields.Monetary(string='Development Cost')

    legal_terms = fields.Html(string='Legal Terms')
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_land_agreement_ir_attachment_rel',
        'agreement_id', 'attachment_id', string='Documents')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('legal_review', 'Legal Review'),
        ('management_review', 'Management Review'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.land.agreement') or 'New'
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    'End Date cannot be before Start Date for agreement "%s".' % rec.name)

    @api.constrains('developer_share_percentage', 'land_owner_share_percentage')
    def _check_shares(self):
        for rec in self:
            total = rec.developer_share_percentage + rec.land_owner_share_percentage
            if total and round(total, 2) > 100.0:
                raise ValidationError(
                    'Developer Share + Land Owner Share cannot exceed 100%% '
                    '(currently %.2f%%) for agreement "%s".' % (total, rec.name))

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError(
                    'Action not allowed. Agreement "%s" must be in state '
                    '"%s" (currently "%s").' % (rec.name, expected, rec.state))

    def action_submit_legal_review(self):
        self._require_state('draft')
        self.write({'state': 'legal_review'})

    def action_submit_management_review(self):
        self._require_state('legal_review')
        self.write({'state': 'management_review'})

    def action_approve(self):
        self._require_state('management_review')
        if not self.env.user.has_group(
                'real_estate_project_management.group_real_estate_director') and \
           not self.env.user.has_group(
                'real_estate_project_management.group_real_estate_administrator'):
            raise UserError('Only a Real Estate Director or Administrator can '
                             'approve a land agreement.')
        self.write({'state': 'approved'})

    def action_activate(self):
        self._require_state('approved')
        self.write({'state': 'active'})
        self.mapped('land_id').write({'state': 'under_agreement'})

    def action_expire(self):
        for rec in self:
            if rec.state != 'active':
                raise UserError('Only active agreements can expire.')
        self.write({'state': 'expired'})

    def action_terminate(self):
        for rec in self:
            if rec.state not in ('approved', 'active'):
                raise UserError('Only approved or active agreements can be terminated.')
        self.write({'state': 'terminated'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
