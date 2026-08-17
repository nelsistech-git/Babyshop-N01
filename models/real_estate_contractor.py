# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstateContractor(models.Model):
    """A contractor engaged for a specific trade/project, linked to
    res.partner (no duplicate contact data)."""
    _name = 'real.estate.contractor'
    _description = 'Real Estate Contractor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='Contractor Contact',
                                  required=True, tracking=True, ondelete='restrict')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    trade = fields.Selection([
        ('civil', 'Civil'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('interior', 'Interior'),
        ('lift', 'Lift'),
        ('fire', 'Fire'),
        ('landscaping', 'Landscaping'),
        ('security', 'Security'),
        ('other', 'Other'),
    ], string='Trade', required=True, default='civil', tracking=True)

    contract_number = fields.Char(string='Contract Number', copy=False, tracking=True,
                                   default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project', tracking=True)
    work_package_ids = fields.One2many('real.estate.work.package', 'contractor_id',
                                        string='Work Packages')

    contract_value = fields.Monetary(string='Contract Value', tracking=True)
    advance_percentage = fields.Float(string='Advance %', digits=(5, 2))
    retention_percentage = fields.Float(string='Retention %', digits=(5, 2))

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_contractor_ir_attachment_rel',
        'contractor_id', 'attachment_id', string='Documents')

    bill_ids = fields.One2many('real.estate.contractor.bill', 'contractor_id', string='Bills')
    bill_count = fields.Integer(compute='_compute_bill_count')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    _sql_constraints = [
        ('contract_number_uniq', 'unique(contract_number, company_id)',
         'Contract Number must be unique per company.'),
    ]

    @api.depends('partner_id.name', 'trade')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%s)' % (rec.partner_id.name or '', rec.trade or '') \
                if rec.partner_id else (rec.trade or '')

    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('contract_number', 'New') == 'New':
                vals['contract_number'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.contractor') or 'New'
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError('End Date cannot be before Start Date for '
                                       'contractor "%s".' % rec.display_name)

    @api.constrains('advance_percentage', 'retention_percentage')
    def _check_percentages(self):
        for rec in self:
            if not (0 <= rec.advance_percentage <= 100):
                raise ValidationError('Advance % must be between 0 and 100.')
            if not (0 <= rec.retention_percentage <= 100):
                raise ValidationError('Retention % must be between 0 and 100.')

    def action_activate(self):
        self.write({'status': 'active'})

    def action_complete(self):
        self.write({'status': 'completed'})

    def action_terminate(self):
        self.write({'status': 'terminated'})

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contractor Bills',
            'res_model': 'real.estate.contractor.bill',
            'view_mode': 'tree,form',
            'domain': [('contractor_id', '=', self.id)],
            'context': {'default_contractor_id': self.id},
        }
