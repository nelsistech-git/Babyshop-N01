# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateSiteReport(models.Model):
    _name = 'real.estate.site.report'
    _description = 'Real Estate Site Daily Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(string='Report Number', copy=False, tracking=True,
                        default='New', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, tracking=True, ondelete='restrict')
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    engineer_id = fields.Many2one('res.users', string='Engineer',
                                   default=lambda self: self.env.user)

    weather = fields.Selection([
        ('sunny', 'Sunny'), ('cloudy', 'Cloudy'), ('rainy', 'Rainy'),
        ('stormy', 'Stormy'), ('other', 'Other'),
    ], string='Weather')
    workers_present = fields.Integer(string='Workers Present')
    contractor_id = fields.Many2one('real.estate.contractor', string='Contractor')

    work_completed = fields.Text(string='Work Completed')
    materials_used = fields.Text(string='Materials Used')
    equipment_used = fields.Text(string='Equipment Used')
    problems = fields.Text(string='Problems')
    safety_issues = fields.Text(string='Safety Issues')
    progress = fields.Float(string='Progress %', digits=(5, 2))

    photo_ids = fields.Many2many(
        'ir.attachment', 'real_estate_site_report_ir_attachment_rel',
        'report_id', 'attachment_id', string='Photos / Documents')
    remarks = fields.Text(string='Remarks')

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.site.report') or 'New'
        return super().create(vals_list)
