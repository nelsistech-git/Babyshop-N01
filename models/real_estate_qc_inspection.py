# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateQcInspection(models.Model):
    """A quality-control inspection against a project/building/unit/work
    package, optionally seeded from a configurable checklist template."""
    _name = 'real.estate.qc.inspection'
    _description = 'Real Estate QC Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Inspection Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, tracking=True, ondelete='restrict')
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    unit_id = fields.Many2one('real.estate.unit', string='Unit',
                               domain="[('project_id', '=', project_id)]")
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")

    inspection_type = fields.Selection([
        ('civil', 'Civil'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('finishing', 'Finishing'),
        ('final', 'Final'),
        ('other', 'Other'),
    ], string='Inspection Type', required=True, default='civil', tracking=True)

    inspector_id = fields.Many2one('res.users', string='Inspector',
                                    default=lambda self: self.env.user, tracking=True)
    inspection_date = fields.Date(string='Inspection Date', default=fields.Date.context_today)

    checklist_template_id = fields.Many2one('real.estate.qc.checklist.template',
                                             string='Checklist Template',
                                             domain="[('category', '=', inspection_type)]")
    line_ids = fields.One2many('real.estate.qc.inspection.line', 'inspection_id',
                                string='Checklist Results')
    line_count = fields.Integer(compute='_compute_line_stats')
    failed_line_count = fields.Integer(compute='_compute_line_stats')

    result = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('conditional', 'Conditional'),
    ], string='Result', default='pending', tracking=True, required=True, copy=False)

    remarks = fields.Text(string='Remarks')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_qc_inspection_ir_attachment_rel',
        'inspection_id', 'attachment_id', string='Photos / Attachments')

    defect_ids = fields.One2many('real.estate.defect', 'qc_inspection_id', string='Defects Raised')
    defect_count = fields.Integer(compute='_compute_line_stats')

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)

    @api.depends('line_ids.result', 'defect_ids')
    def _compute_line_stats(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.failed_line_count = len(rec.line_ids.filtered(lambda l: l.result == 'fail'))
            rec.defect_count = len(rec.defect_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.qc.inspection') or 'New'
        return super().create(vals_list)

    @api.onchange('checklist_template_id')
    def _onchange_checklist_template_id(self):
        if self.checklist_template_id:
            lines = [(5, 0, 0)]
            for tline in self.checklist_template_id.line_ids:
                lines.append((0, 0, {
                    'item_name': tline.item_name,
                    'description': tline.description,
                    'result': 'pending',
                }))
            self.line_ids = lines

    def action_recommend_result(self):
        """Suggest a Result based on the checklist line outcomes; the
        inspector can still override it before saving."""
        for rec in self:
            if not rec.line_ids:
                continue
            results = rec.line_ids.mapped('result')
            if any(r == 'fail' for r in results):
                rec.result = 'failed'
            elif all(r == 'pass' for r in results):
                rec.result = 'passed'
            elif any(r == 'pending' for r in results):
                rec.result = 'pending'
            else:
                rec.result = 'conditional'

    def action_mark_passed(self):
        self.write({'result': 'passed'})

    def action_mark_failed(self):
        self.write({'result': 'failed'})

    def action_mark_conditional(self):
        self.write({'result': 'conditional'})
