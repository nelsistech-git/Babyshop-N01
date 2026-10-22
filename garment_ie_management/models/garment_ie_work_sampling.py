# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Work Sampling (SRS s.52, "Work Study") — random-interval activity
observations on a line used to estimate the ratio of working / idle /
waiting / rework time without a full continuous time study.
"""
from odoo import api, fields, models, _


class GarmentIeWorkSampling(models.Model):
    _name = 'garment.ie.work.sampling'
    _description = 'Garment IE Work Sampling Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'study_number'

    study_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    observer_id = fields.Many2one('garment.hr.employee', string='Observer (IE Engineer)')

    observation_ids = fields.One2many('garment.ie.work.sampling.line', 'sampling_id', string='Observations')
    total_observations = fields.Integer(string='Total Observations', compute='_compute_ratios', store=True)
    working_pct = fields.Float(string='Working (%)', compute='_compute_ratios', store=True)
    idle_pct = fields.Float(string='Idle (%)', compute='_compute_ratios', store=True)
    waiting_pct = fields.Float(string='Waiting (%)', compute='_compute_ratios', store=True)
    other_pct = fields.Float(string='Rework / Other (%)', compute='_compute_ratios', store=True)

    status = fields.Selection([('draft', 'Draft'), ('completed', 'Completed')], string='Status',
                               default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('observation_ids.activity')
    def _compute_ratios(self):
        for rec in self:
            lines = rec.observation_ids
            total = len(lines)
            rec.total_observations = total
            if not total:
                rec.working_pct = rec.idle_pct = rec.waiting_pct = rec.other_pct = 0.0
                continue
            rec.working_pct = len(lines.filtered(lambda l: l.activity == 'working')) / total * 100.0
            rec.idle_pct = len(lines.filtered(lambda l: l.activity == 'idle')) / total * 100.0
            rec.waiting_pct = len(lines.filtered(lambda l: l.activity == 'waiting')) / total * 100.0
            rec.other_pct = len(lines.filtered(lambda l: l.activity in ('rework', 'other'))) / total * 100.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('study_number', _('New')) == _('New'):
                vals['study_number'] = self.env['ir.sequence'].next_by_code('garment.ie.work.sampling') or _('New')
        return super().create(vals_list)

    def action_complete(self):
        self.write({'status': 'completed'})


class GarmentIeWorkSamplingLine(models.Model):
    _name = 'garment.ie.work.sampling.line'
    _description = 'Garment IE Work Sampling Observation'
    _order = 'sampling_id, observation_time'

    sampling_id = fields.Many2one('garment.ie.work.sampling', string='Work Sampling Study', required=True,
                                   ondelete='cascade')
    observation_time = fields.Datetime(string='Observation Time', default=fields.Datetime.now, required=True)
    operator_id = fields.Many2one('garment.hr.employee', string='Operator')
    operation_id = fields.Many2one('garment.ie.operation', string='Operation')
    activity = fields.Selection([
        ('working', 'Working'), ('idle', 'Idle'), ('waiting', 'Waiting'),
        ('rework', 'Rework'), ('other', 'Other'),
    ], string='Activity', default='working', required=True)
    remarks = fields.Char(string='Remarks')
