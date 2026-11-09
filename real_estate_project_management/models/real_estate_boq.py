# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateBoq(models.Model):
    """Bill of Quantities header for a project (optionally scoped to one
    work package). Lines hold the item-level estimated vs approved vs
    actual quantities/amounts."""
    _name = 'real.estate.boq'
    _description = 'Real Estate Bill of Quantities'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='BOQ Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, ondelete='cascade', tracking=True)
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")
    date = fields.Date(string='Date', default=fields.Date.context_today)

    line_ids = fields.One2many('real.estate.boq.line', 'boq_id', string='BOQ Lines')
    total_estimated_amount = fields.Monetary(string='Total Estimated', compute='_compute_totals', store=True)
    total_approved_amount = fields.Monetary(string='Total Approved', compute='_compute_totals', store=True)
    total_actual_amount = fields.Monetary(string='Total Actual', compute='_compute_totals', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('line_ids.estimated_amount', 'line_ids.approved_amount', 'line_ids.actual_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_estimated_amount = sum(rec.line_ids.mapped('estimated_amount'))
            rec.total_approved_amount = sum(rec.line_ids.mapped('approved_amount'))
            rec.total_actual_amount = sum(rec.line_ids.mapped('actual_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.boq') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
