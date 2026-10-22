# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
SMV Master Database (SRS s.7-9, s.39-40, s.50) — Style x Operation x Machine
x Skill Level, with Basic Time + Allowance = SMV and an IE Manager approval
workflow ("New SMV Created -> IE Manager Approval -> Production Update").
"""
from odoo import api, fields, models, _

from .garment_ie_operation import MACHINE_TYPE_SELECTION, SKILL_LEVEL_SELECTION


class GarmentIeSmv(models.Model):
    _name = 'garment.ie.smv'
    _description = 'Garment IE SMV Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'style_id, operation_id'
    _rec_name = 'smv_number'

    smv_number = fields.Char(string='SMV Reference', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True, tracking=True)
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Routing Operation Reference',
                                       help='Optional link back to the style Operation Routing line this '
                                            'SMV was studied for.')
    machine_type = fields.Selection(MACHINE_TYPE_SELECTION, string='Machine Type')
    skill_level = fields.Selection(SKILL_LEVEL_SELECTION, string='Skill Level', default='skilled')

    basic_time = fields.Float(string='Basic Time (Minutes)', digits=(6, 3), required=True, tracking=True)
    allowance_line_ids = fields.One2many('garment.ie.smv.allowance.line', 'smv_id', string='Allowance Breakdown')
    allowance_pct = fields.Float(string='Total Allowance (%)', compute='_compute_smv', store=True)
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3), compute='_compute_smv', store=True, tracking=True)

    version = fields.Char(string='Version', default='1.0')
    status = fields.Selection([
        ('draft', 'Draft'), ('pending_approval', 'Pending IE Manager Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('obsolete', 'Obsolete'),
    ], string='Status', default='draft', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)

    time_study_ids = fields.One2many('garment.ie.time.study', 'smv_id', string='Source Time Studies')
    time_study_count = fields.Integer(string='Time Studies', compute='_compute_time_study_count')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('basic_time', 'allowance_line_ids.percentage')
    def _compute_smv(self):
        for rec in self:
            rec.allowance_pct = sum(rec.allowance_line_ids.mapped('percentage'))
            rec.smv = rec.basic_time * (1 + rec.allowance_pct / 100.0)

    def _compute_time_study_count(self):
        for rec in self:
            rec.time_study_count = len(rec.time_study_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('smv_number', _('New')) == _('New'):
                vals['smv_number'] = self.env['ir.sequence'].next_by_code('garment.ie.smv') or _('New')
        return super().create(vals_list)

    def action_submit_for_approval(self):
        self.write({'status': 'pending_approval'})

    def action_approve(self):
        self.write({
            'status': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_reset_to_draft(self):
        self.write({'status': 'draft', 'approved_by_id': False, 'approved_date': False})

    def action_obsolete(self):
        self.write({'status': 'obsolete', 'active': False})

    def action_view_time_studies(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'garment_ie_management.action_garment_ie_time_study')
        action['domain'] = [('smv_id', '=', self.id)]
        return action


class GarmentIeSmvAllowanceLine(models.Model):
    _name = 'garment.ie.smv.allowance.line'
    _description = 'Garment IE SMV Allowance Line'
    _order = 'smv_id, id'

    smv_id = fields.Many2one('garment.ie.smv', string='SMV Master', required=True, ondelete='cascade')
    allowance_type_id = fields.Many2one('garment.ie.allowance.type', string='Allowance Type', required=True)
    percentage = fields.Float(string='Allowance (%)', required=True)

    @api.onchange('allowance_type_id')
    def _onchange_allowance_type_id(self):
        if self.allowance_type_id:
            self.percentage = self.allowance_type_id.default_pct
