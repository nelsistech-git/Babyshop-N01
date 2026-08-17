# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateWarranty(models.Model):
    """Post-handover warranty claim / snag reported by a customer.
    Covers both 'warranty' and 'snag' use cases from spec section 49 in
    a single model rather than two near-duplicates, consistent with the
    'avoid unnecessary database duplication' rule applied throughout this
    module (see Phase 7's shared Collection model for the same pattern)."""
    _name = 'real.estate.warranty'
    _description = 'Real Estate Warranty / Snag Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Claim Number', copy=False, tracking=True,
                        default='New', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                   tracking=True, ondelete='restrict')
    unit_id = fields.Many2one('real.estate.unit', string='Unit', required=True,
                               tracking=True, ondelete='restrict')
    project_id = fields.Many2one(related='unit_id.project_id', store=True, readonly=True)
    handover_id = fields.Many2one('real.estate.handover', string='Handover',
                                   domain="[('unit_id', '=', unit_id)]")
    warranty_expiry_date = fields.Date(related='handover_id.warranty_expiry_date', readonly=True)
    # COMMENTED OUT (2026-08-15): computed non-stored field is not searchable.
    # The search view uses it in a filter domain, which failed install with
    # 'Unsearchable field is_under_warranty ... in domain of <filter
    # name="filter_expired">'. store=True makes it searchable (depends already
    # declared on reported_date + warranty_expiry_date).
    # is_under_warranty = fields.Boolean(string='Within Warranty Period',
    #                                     compute='_compute_is_under_warranty')
    is_under_warranty = fields.Boolean(string='Within Warranty Period',
                                        compute='_compute_is_under_warranty',
                                        store=True)

    category = fields.Selection([
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('door', 'Door'),
        ('window', 'Window'),
        ('paint', 'Paint'),
        ('flooring', 'Flooring'),
        ('bathroom', 'Bathroom'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other', tracking=True)

    description = fields.Text(string='Description', required=True)
    reported_date = fields.Date(string='Reported Date', default=fields.Date.context_today, tracking=True)

    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    contractor_id = fields.Many2one('real.estate.contractor', string='Contractor')
    resolution_notes = fields.Text(string='Resolution Notes')

    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_warranty_ir_attachment_rel',
        'warranty_id', 'attachment_id', string='Photos / Attachments')

    status = fields.Selection([
        ('reported', 'Reported'),
        ('inspection', 'Inspection'),
        ('assigned', 'Assigned'),
        ('repair', 'Repair'),
        ('qc', 'QC'),
        ('closed', 'Closed'),
    ], string='Status', default='reported', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='unit_id.company_id', store=True, readonly=True)

    @api.depends('reported_date', 'warranty_expiry_date')
    def _compute_is_under_warranty(self):
        for rec in self:
            if not rec.warranty_expiry_date or not rec.reported_date:
                rec.is_under_warranty = False
            else:
                rec.is_under_warranty = rec.reported_date <= rec.warranty_expiry_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.warranty') or 'New'
        return super().create(vals_list)

    def _require_state(self, expected):
        for rec in self:
            if rec.status != expected:
                raise UserError('Claim "%s" must be in state "%s" for this '
                                 'action (currently "%s").' % (rec.name, expected, rec.status))

    def action_start_inspection(self):
        self._require_state('reported')
        self.write({'status': 'inspection'})

    def action_assign(self):
        self._require_state('inspection')
        for rec in self:
            if not rec.assigned_user_id:
                raise UserError('Set "Assigned To" before assigning this claim.')
        self.write({'status': 'assigned'})

    def action_start_repair(self):
        self._require_state('assigned')
        self.write({'status': 'repair'})

    def action_send_qc(self):
        self._require_state('repair')
        self.write({'status': 'qc'})

    def action_close(self):
        self._require_state('qc')
        self.write({'status': 'closed'})

    def action_reopen(self):
        for rec in self:
            if rec.status != 'closed':
                raise UserError('Only closed claims can be reopened.')
        self.write({'status': 'reported'})
