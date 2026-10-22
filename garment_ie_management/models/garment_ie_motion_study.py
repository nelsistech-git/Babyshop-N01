# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Motion Study Management (SRS s.30) — analyzes operator movement (walking
distance, hand movement, material access) to reduce unnecessary motion."""
from odoo import api, fields, models, _


class GarmentIeMotionStudy(models.Model):
    _name = 'garment.ie.motion.study'
    _description = 'Garment IE Motion Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'study_number'

    study_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True, tracking=True)
    workstation_id = fields.Many2one('garment.ie.workstation', string='Workstation')

    problem_description = fields.Text(string='Problem', help='e.g. "Operator walks 5 meters to accessory box"')
    walking_distance_before = fields.Float(string='Walking Distance Before (m)')
    walking_distance_after = fields.Float(string='Walking Distance After (m)')
    hand_movements_before = fields.Integer(string='Hand Movements Before')
    hand_movements_after = fields.Integer(string='Hand Movements After')

    solution_description = fields.Text(string='Solution', help='e.g. "Move accessory box closer"')
    time_saving_seconds = fields.Float(string='Time Saving (Sec/Cycle)')

    responsible_id = fields.Many2one('garment.hr.employee', string='IE Engineer')
    status = fields.Selection([
        ('draft', 'Draft'), ('proposed', 'Proposed'), ('implemented', 'Implemented'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('study_number', _('New')) == _('New'):
                vals['study_number'] = self.env['ir.sequence'].next_by_code('garment.ie.motion.study') or _('New')
        return super().create(vals_list)

    def action_propose(self):
        self.write({'status': 'proposed'})

    def action_implement(self):
        self.write({'status': 'implemented'})
