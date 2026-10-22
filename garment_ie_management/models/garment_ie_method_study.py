# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Method Study Management (SRS s.29) — current vs. improved operation
method/machine setting/workstation layout, with a time-saving %."""
from odoo import api, fields, models, _


class GarmentIeMethodStudy(models.Model):
    _name = 'garment.ie.method.study'
    _description = 'Garment IE Method Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'study_number'

    study_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style')
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True, tracking=True)
    study_area = fields.Selection([
        ('operation_method', 'Operation Method'),
        ('machine_setting', 'Machine Setting'),
        ('operator_movement', 'Operator Movement'),
        ('workstation_layout', 'Workstation Layout'),
    ], string='Study Area', default='operation_method', required=True)

    current_method_steps = fields.Integer(string='Current Method (Steps)')
    current_method_description = fields.Text(string='Current Method')
    current_cycle_time = fields.Float(string='Current Cycle Time (Min)', digits=(6, 3))

    improved_method_steps = fields.Integer(string='Improved Method (Steps)')
    improved_method_description = fields.Text(string='Improved Method')
    improved_cycle_time = fields.Float(string='Improved Cycle Time (Min)', digits=(6, 3))

    time_saving_pct = fields.Float(string='Time Saving (%)', compute='_compute_time_saving', store=True)

    responsible_id = fields.Many2one('garment.hr.employee', string='IE Engineer')
    status = fields.Selection([
        ('draft', 'Draft'), ('proposed', 'Proposed'), ('approved', 'Approved'),
        ('implemented', 'Implemented'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    implemented_date = fields.Date(string='Implemented Date')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('current_cycle_time', 'improved_cycle_time')
    def _compute_time_saving(self):
        for rec in self:
            rec.time_saving_pct = ((rec.current_cycle_time - rec.improved_cycle_time) / rec.current_cycle_time * 100.0
                                    if rec.current_cycle_time else 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('study_number', _('New')) == _('New'):
                vals['study_number'] = self.env['ir.sequence'].next_by_code('garment.ie.method.study') or _('New')
        return super().create(vals_list)

    def action_propose(self):
        self.write({'status': 'proposed'})

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_implement(self):
        self.write({'status': 'implemented', 'implemented_date': fields.Date.context_today(self)})
