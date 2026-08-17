# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstateLandOwner(models.Model):
    """A person or entity that owns land acquired/managed by the company.

    Reuses res.partner for name/contact/address/email so we do not
    duplicate standard Odoo contact data. Only real-estate specific
    attributes live on this model.
    """
    _name = 'real.estate.land.owner'
    _description = 'Real Estate Land Owner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'id desc'

    name = fields.Char(string='Owner Reference', copy=False, tracking=True,
                        help='Internal short reference/code for this owner record.')
    partner_id = fields.Many2one(
        'res.partner', string='Related Contact', required=True, tracking=True,
        ondelete='restrict',
        help='Standard Odoo contact holding name, phone, mobile, email and address.')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    nid_passport = fields.Char(string='NID / Passport No.', tracking=True)
    tax_id_number = fields.Char(string='Tax Identification No.', tracking=True)

    bank_name = fields.Char(string='Bank Name')
    bank_branch = fields.Char(string='Bank Branch')
    bank_account_name = fields.Char(string='Account Holder Name')
    bank_account_number = fields.Char(string='Account Number')
    bank_routing_number = fields.Char(string='Routing Number')

    ownership_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('trust', 'Trust'),
        ('government', 'Government'),
        ('other', 'Other'),
    ], string='Ownership Type', default='individual', tracking=True, required=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='draft', tracking=True, required=True)

    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_land_owner_ir_attachment_rel',
        'owner_id', 'attachment_id', string='Documents')

    land_ownership_ids = fields.One2many(
        'real.estate.land.ownership', 'owner_id', string='Land Ownerships')
    land_count = fields.Integer(compute='_compute_land_count', string='Land Count')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    # Convenience related fields from partner (readonly display helpers)
    email = fields.Char(related='partner_id.email', readonly=True, store=False)
    phone = fields.Char(related='partner_id.phone', readonly=True, store=False)
    mobile = fields.Char(related='partner_id.mobile', readonly=True, store=False)
    # COMMENTED OUT (2026-08-15): 'contact_address_complete' does not exist on
    # res.partner in Odoo 17 (removed upstream). The Odoo 17 field holding the
    # formatted complete address is 'contact_address'. Without this change the
    # module fails to install with:
    # KeyError: 'Field contact_address_complete referenced in related field
    # definition real.estate.land.owner.address does not exist.'
    # address = fields.Char(related='partner_id.contact_address_complete',
    #                        readonly=True, store=False)
    address = fields.Char(related='partner_id.contact_address',
                           readonly=True, store=False)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)',
         'Owner Reference must be unique per company.'),
    ]

    @api.depends('name', 'partner_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.partner_id:
                rec.display_name = '%s - %s' % (rec.name, rec.partner_id.name)
            elif rec.partner_id:
                rec.display_name = rec.partner_id.name
            else:
                rec.display_name = rec.name or ''

    def _compute_land_count(self):
        for rec in self:
            rec.land_count = len(rec.land_ownership_ids.mapped('land_id'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.land.owner') or '/'
        return super().create(vals_list)

    def action_activate(self):
        self.write({'status': 'active'})

    def action_deactivate(self):
        self.write({'status': 'inactive'})

    def action_view_lands(self):
        self.ensure_one()
        land_ids = self.land_ownership_ids.mapped('land_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lands',
            'res_model': 'real.estate.land',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', land_ids)],
        }

    @api.constrains('partner_id', 'company_id')
    def _check_partner_company(self):
        for rec in self:
            if rec.partner_id.company_id and rec.company_id and \
                    rec.partner_id.company_id != rec.company_id:
                raise ValidationError(
                    'The related contact belongs to a different company '
                    'than this land owner record.')
