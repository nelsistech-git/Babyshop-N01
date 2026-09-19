# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwTimeStudy(models.Model):
    _name = 'fw.time.study'
    _description = 'Footwear Time Study (SMV Capture)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Study Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.time.study') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', tracking=True)
    operation_id = fields.Many2one('fw.operation', string='Operation', required=True,
                                    tracking=True)
    date = fields.Date(string='Study Date', default=fields.Date.context_today)
    studied_by = fields.Many2one('res.users', string='Studied By',
                                  default=lambda self: self.env.user)

    reading_ids = fields.One2many('fw.time.study.reading', 'study_id', string='Cycle Readings')
    avg_observed_time = fields.Float(string='Avg. Observed Time (sec)',
                                      compute='_compute_times', store=True)

    performance_rating = fields.Float(string='Performance Rating (%)', default=100.0,
                                       help="Rate the operator's observed pace against normal "
                                            "pace. 100% = normal pace.")
    basic_time = fields.Float(string='Basic Time (sec)', compute='_compute_times', store=True)

    allowance_percent = fields.Float(string='PFD Allowance (%)', default=10.0,
                                      help="Personal, Fatigue & Delay allowance, "
                                           "typically 10-15% in footwear operations.")
    standard_time_seconds = fields.Float(string='Standard Time (sec)',
                                          compute='_compute_times', store=True)
    standard_smv = fields.Float(string='Standard SMV (min)', compute='_compute_times',
                                 store=True, digits=(8, 4))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.time.study') or 'New'
        return super().create(vals_list)

    @api.depends('reading_ids.observed_time', 'performance_rating', 'allowance_percent')
    def _compute_times(self):
        for rec in self:
            readings = rec.reading_ids.mapped('observed_time')
            rec.avg_observed_time = (sum(readings) / len(readings)) if readings else 0.0
            rec.basic_time = rec.avg_observed_time * (rec.performance_rating or 0.0) / 100.0
            rec.standard_time_seconds = rec.basic_time * (1 + (rec.allowance_percent or 0.0) / 100.0)
            rec.standard_smv = rec.standard_time_seconds / 60.0

    def action_approve(self):
        for rec in self:
            if not rec.reading_ids:
                raise UserError("Cannot approve a time study with no cycle readings.")
            rec.operation_id.write({'standard_smv': rec.standard_smv})
        self.write({'state': 'approved'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwTimeStudyReading(models.Model):
    _name = 'fw.time.study.reading'
    _description = 'Time Study Cycle Reading'
    _order = 'cycle_no'

    study_id = fields.Many2one('fw.time.study', string='Time Study', required=True,
                                ondelete='cascade')
    cycle_no = fields.Integer(string='Cycle No.', required=True)
    observed_time = fields.Float(string='Observed Time (sec)', required=True)
    remarks = fields.Char(string='Remarks')
