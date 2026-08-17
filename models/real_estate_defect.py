# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateDefect(models.Model):
    """A defect / non-conformance report raised against a project,
    building, unit or work package - optionally originating from a QC
    Inspection."""
    _name = 'real.estate.defect'
    _description = 'Real Estate Defect / NCR'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Defect Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, tracking=True, ondelete='restrict')
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    unit_id = fields.Many2one('real.estate.unit', string='Unit',
                               domain="[('project_id', '=', project_id)]")
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")
    qc_inspection_id = fields.Many2one('real.estate.qc.inspection', string='Source QC Inspection')

    description = fields.Text(string='Description', required=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='medium', tracking=True)

    contractor_id = fields.Many2one('real.estate.contractor', string='Contractor')
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    due_date = fields.Date(string='Due Date')
    corrective_action = fields.Text(string='Corrective Action')

    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_defect_ir_attachment_rel',
        'defect_id', 'attachment_id', string='Photos / Attachments')

    status = fields.Selection([
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('fixed', 'Fixed'),
        ('reinspection', 'Reinspection'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.defect') or 'New'
        return super().create(vals_list)

    def action_assign(self):
        for rec in self:
            if not rec.assigned_user_id:
                raise UserError('Set "Assigned To" before assigning this defect.')
        self.write({'status': 'assigned'})

    def action_start_progress(self):
        self.write({'status': 'in_progress'})

    def action_mark_fixed(self):
        self.write({'status': 'fixed'})

    def action_send_reinspection(self):
        self.write({'status': 'reinspection'})

    def action_close(self):
        self.write({'status': 'closed'})

    def action_reopen(self):
        self.write({'status': 'open'})
