# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Time Study Management (SRS s.12-16) — stopwatch observations of an operator
on an operation, Normal Time = Observed Time x Performance Rating, allowance
application, and an "Update SMV" action that closes the loop into the SMV
Master (Select Operation -> Observe Operator -> Record Time -> Calculate
Average -> Update SMV).
"""
from odoo import api, fields, models, _

from .garment_ie_operation import MACHINE_TYPE_SELECTION


class GarmentIeTimeStudy(models.Model):
    _name = 'garment.ie.time.study'
    _description = 'Garment IE Time Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'study_number'

    study_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True, tracking=True)
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Routing Operation Reference')
    work_order_id = fields.Many2one('garment.work.order', string='Work Order Observed')
    employee_id = fields.Many2one('garment.hr.employee', string='Operator', required=True, tracking=True)
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    machine_type = fields.Selection(MACHINE_TYPE_SELECTION, string='Machine Type')
    date = fields.Date(string='Study Date', default=fields.Date.context_today, required=True)
    study_type = fields.Selection([
        ('stopwatch', 'Stopwatch Time Study'), ('continuous', 'Continuous Timing'),
        ('snap_back', 'Snap Back Timing'),
    ], string='Study Type', default='stopwatch', required=True)

    observation_ids = fields.One2many('garment.ie.time.study.line', 'study_id', string='Observations')
    observation_count = fields.Integer(string='Observation Count', compute='_compute_observations', store=True)
    avg_cycle_time = fields.Float(string='Average Observed Time (Min)', digits=(6, 3),
                                   compute='_compute_observations', store=True)
    avg_rating_pct = fields.Float(string='Average Performance Rating (%)',
                                   compute='_compute_observations', store=True)
    normal_time = fields.Float(string='Normal Time (Min)', digits=(6, 3),
                                compute='_compute_observations', store=True,
                                help='Normal Time = Observed Time x Performance Rating')

    allowance_line_ids = fields.One2many('garment.ie.time.study.allowance.line', 'study_id',
                                          string='Allowance Breakdown')
    allowance_pct = fields.Float(string='Total Allowance (%)', compute='_compute_standard_time', store=True)
    standard_time = fields.Float(string='Standard Time / SMV (Min)', digits=(6, 3),
                                  compute='_compute_standard_time', store=True, tracking=True)

    smv_id = fields.Many2one('garment.ie.smv', string='Linked SMV Master', readonly=True, copy=False)
    status = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('smv_updated', 'SMV Updated'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('observation_ids.cycle_time', 'observation_ids.rating_factor')
    def _compute_observations(self):
        for rec in self:
            lines = rec.observation_ids
            rec.observation_count = len(lines)
            rec.avg_cycle_time = sum(lines.mapped('cycle_time')) / len(lines) if lines else 0.0
            rec.avg_rating_pct = sum(lines.mapped('rating_factor')) / len(lines) if lines else 100.0
            rec.normal_time = rec.avg_cycle_time * (rec.avg_rating_pct / 100.0)

    @api.depends('normal_time', 'allowance_line_ids.percentage')
    def _compute_standard_time(self):
        for rec in self:
            rec.allowance_pct = sum(rec.allowance_line_ids.mapped('percentage'))
            rec.standard_time = rec.normal_time * (1 + rec.allowance_pct / 100.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('study_number', _('New')) == _('New'):
                vals['study_number'] = self.env['ir.sequence'].next_by_code('garment.ie.time.study') or _('New')
        return super().create(vals_list)

    def action_mark_completed(self):
        self.write({'status': 'completed'})

    def action_update_smv(self):
        """Update SMV (SRS s.12): create or refresh the SMV Master record for
        this style/operation/machine from the studied Normal Time + allowance."""
        Smv = self.env['garment.ie.smv']
        for rec in self:
            allowance_vals = [(0, 0, {
                'allowance_type_id': line.allowance_type_id.id,
                'percentage': line.percentage,
            }) for line in rec.allowance_line_ids]
            smv = Smv.search([
                ('style_id', '=', rec.style_id.id),
                ('operation_id', '=', rec.operation_id.id),
                ('machine_type', '=', rec.machine_type),
            ], limit=1)
            vals = {
                'style_id': rec.style_id.id,
                'operation_id': rec.operation_id.id,
                'routing_line_id': rec.routing_line_id.id,
                'machine_type': rec.machine_type,
                'basic_time': rec.normal_time,
                'allowance_line_ids': [(5, 0, 0)] + allowance_vals,
            }
            if smv:
                smv.write(vals)
            else:
                smv = Smv.create(vals)
            rec.write({'smv_id': smv.id, 'status': 'smv_updated'})
        return True

    def action_view_smv(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('garment_ie_management.action_garment_ie_smv')
        action['res_id'] = self.smv_id.id
        action['view_mode'] = 'form'
        return action


class GarmentIeTimeStudyLine(models.Model):
    """Stopwatch cycle observation (SRS s.13-14)."""
    _name = 'garment.ie.time.study.line'
    _description = 'Garment IE Time Study Observation'
    _order = 'study_id, cycle_no'

    study_id = fields.Many2one('garment.ie.time.study', string='Time Study', required=True, ondelete='cascade')
    cycle_no = fields.Integer(string='Observation #', required=True)
    start_time = fields.Float(string='Start Time (Min)')
    end_time = fields.Float(string='End Time (Min)')
    cycle_time = fields.Float(string='Cycle Time (Min)', digits=(6, 3), compute='_compute_cycle_time', store=True)
    rating_factor = fields.Float(string='Performance Rating (%)', default=100.0)
    normal_time = fields.Float(string='Normal Time (Min)', digits=(6, 3), compute='_compute_cycle_time', store=True)
    remarks = fields.Char(string='Remarks')

    @api.depends('start_time', 'end_time', 'rating_factor')
    def _compute_cycle_time(self):
        for rec in self:
            rec.cycle_time = max(rec.end_time - rec.start_time, 0.0)
            rec.normal_time = rec.cycle_time * (rec.rating_factor / 100.0)


class GarmentIeTimeStudyAllowanceLine(models.Model):
    _name = 'garment.ie.time.study.allowance.line'
    _description = 'Garment IE Time Study Allowance Line'
    _order = 'study_id, id'

    study_id = fields.Many2one('garment.ie.time.study', string='Time Study', required=True, ondelete='cascade')
    allowance_type_id = fields.Many2one('garment.ie.allowance.type', string='Allowance Type', required=True)
    percentage = fields.Float(string='Allowance (%)', required=True)

    @api.onchange('allowance_type_id')
    def _onchange_allowance_type_id(self):
        if self.allowance_type_id:
            self.percentage = self.allowance_type_id.default_pct
