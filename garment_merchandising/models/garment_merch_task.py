# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchTask(models.Model):
    """Merchandising Task (Garment Merchandising Management System SRS —
    section 5 department structure: Senior/Junior/Production Merchandiser
    responsibilities such as Sample Follow-up, TNA Update, Documentation,
    Production Tracking, Delivery Follow-up; section 40 database model
    'garment.merch.task'; dashboard 'Merchandiser Workload' chart).

    A lightweight to-do/workload tracker for the merchandising desk — not a
    replacement for the detailed follow-up owned by Sample Management, TNA
    or Order Management, but the merchandiser's own task list linking back
    to those records."""
    _name = 'garment.merch.task'
    _description = 'Garment Merchandising Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, priority desc'

    task_number = fields.Char(string='Task Number', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Task', required=True)
    task_type = fields.Selection([
        ('sample_followup', 'Sample Follow-up'),
        ('tna_update', 'TNA Update'),
        ('documentation', 'Documentation'),
        ('production_tracking', 'Production Tracking'),
        ('delivery_followup', 'Delivery Follow-up'),
        ('buyer_communication', 'Buyer Communication'),
        ('negotiation_followup', 'Negotiation Follow-up'),
        ('costing_followup', 'Costing Follow-up'),
        ('other', 'Other'),
    ], string='Task Type', default='other', required=True, tracking=True)

    inquiry_id = fields.Many2one('garment.merch.inquiry', string='Inquiry', ondelete='cascade')
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Order Confirmation',
                                             ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')

    assigned_to_id = fields.Many2one('res.users', string='Assigned To', default=lambda s: s.env.user, tracking=True)
    # Department roles per SRS section 5 (Merchandising Manager / Senior /
    # Junior / Production Merchandiser).
    department_role = fields.Selection([
        ('merchandising_manager', 'Merchandising Manager'),
        ('senior_merchandiser', 'Senior Merchandiser'),
        ('junior_merchandiser', 'Junior Merchandiser'),
        ('production_merchandiser', 'Production Merchandiser'),
    ], string='Department Role')

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')

    due_date = fields.Date(string='Due Date', tracking=True)
    completed_date = fields.Date(string='Completed Date', readonly=True, copy=False)
    status = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)

    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('due_date', 'status')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.due_date and rec.due_date < today and rec.status not in ('done', 'cancelled'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('task_number', _('New')) == _('New'):
                vals['task_number'] = self.env['ir.sequence'].next_by_code('garment.merch.task') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'status': 'in_progress'})

    def action_mark_done(self):
        self.write({'status': 'done', 'completed_date': fields.Date.context_today(self)})

    def action_cancel(self):
        self.write({'status': 'cancelled'})
