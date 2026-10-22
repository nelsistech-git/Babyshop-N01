# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Preventive Maintenance Management (Maintenance & Asset Mgmt SRS sec.
11-13, CMMS SRS sec. 11, 13). Workflow per both source SRS documents:
Maintenance Plan Created -> Schedule Generated -> Technician Assigned ->
Work Order executed -> Report Updated (schedule auto-advances).
"""
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

FREQUENCY_DELTA = {
    'daily': relativedelta(days=1),
    'weekly': relativedelta(weeks=1),
    'monthly': relativedelta(months=1),
    'quarterly': relativedelta(months=3),
    'yearly': relativedelta(years=1),
}


class GarmentMaintenancePlan(models.Model):
    _name = 'garment.maintenance.plan'
    _description = 'Garment Preventive Maintenance Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_due_date'

    name = fields.Char(string='Plan Number', copy=False, readonly=True, default=lambda s: _('New'))
    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine', required=True, tracking=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine', tracking=True)
    asset_id = fields.Many2one('garment.asset', string='Asset', tracking=True)
    equipment_name = fields.Char(string='Equipment', compute='_compute_equipment_name', store=True)

    task_description = fields.Char(string='Maintenance Task', required=True, help='e.g. Oil Change')
    maintenance_type = fields.Selection([
        ('daily', 'Daily Maintenance'),
        ('weekly', 'Weekly Maintenance'),
        ('monthly', 'Monthly Maintenance'),
        ('quarterly', 'Quarterly Maintenance'),
        ('yearly', 'Yearly Maintenance'),
        ('custom', 'Custom Interval'),
    ], string='Frequency', required=True, default='monthly', tracking=True)
    custom_interval_days = fields.Integer(string='Custom Interval (Days)')
    checklist_id = fields.Many2one('garment.maintenance.checklist', string='Checklist Template')
    technician_id = fields.Many2one('garment.hr.employee', string='Assigned Technician',
                                     domain=[('is_maintenance_technician', '=', True)], tracking=True)

    start_date = fields.Date(string='Plan Start Date', default=fields.Date.context_today, required=True)
    last_done_date = fields.Date(string='Last Completed Date')
    next_due_date = fields.Date(string='Next Due Date', tracking=True, required=True,
                                 default=fields.Date.context_today)

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True)

    workorder_ids = fields.One2many('garment.maintenance.workorder', 'plan_id', string='Generated Work Orders')
    workorder_count = fields.Integer(compute='_compute_workorder_count')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('machine_id.machine_number', 'machine_id.name', 'asset_id.name', 'asset_id.asset_code')
    def _compute_equipment_name(self):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.equipment_name = rec.machine_id.name or rec.machine_id.machine_number
            elif rec.equipment_type == 'asset' and rec.asset_id:
                rec.equipment_name = '%s [%s]' % (rec.asset_id.name, rec.asset_id.asset_code)
            else:
                rec.equipment_name = False

    @api.depends('workorder_ids')
    def _compute_workorder_count(self):
        for rec in self:
            rec.workorder_count = len(rec.workorder_ids)

    @api.onchange('equipment_type')
    def _onchange_equipment_type(self):
        self.machine_id = False
        self.asset_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.maintenance.plan') or _('New')
        return super().create(vals_list)

    def _get_interval(self):
        self.ensure_one()
        if self.maintenance_type == 'custom':
            return relativedelta(days=self.custom_interval_days or 30)
        return FREQUENCY_DELTA.get(self.maintenance_type, relativedelta(months=1))

    def action_generate_workorder(self):
        """Manually (or from a button) generate the next PM Work Order for this plan."""
        Workorder = self.env['garment.maintenance.workorder']
        results = Workorder
        for rec in self:
            if rec.status != 'scheduled':
                raise UserError(_('Only a scheduled plan can generate a work order.'))
            wo = Workorder.create({
                'wo_type': 'preventive',
                'equipment_type': rec.equipment_type,
                'machine_id': rec.machine_id.id,
                'asset_id': rec.asset_id.id,
                'plan_id': rec.id,
                'checklist_id': rec.checklist_id.id,
                'technician_id': rec.technician_id.id,
                'priority': 'medium',
                'problem_description': rec.task_description,
            })
            results |= wo
        return results

    def action_advance_schedule(self, done_date=None):
        """Called by the Work Order when a PM job linked to this plan is
        completed: records completion and rolls the schedule forward."""
        done_date = done_date or fields.Date.context_today(self)
        for rec in self:
            next_due = done_date + rec._get_interval()
            rec.write({'last_done_date': done_date, 'next_due_date': next_due})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_reschedule(self):
        self.write({'status': 'scheduled'})

    def action_view_workorders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders'), 'type': 'ir.actions.act_window', 'res_model': 'garment.maintenance.workorder',
            'view_mode': 'tree,form', 'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id, 'default_equipment_type': self.equipment_type,
                        'default_machine_id': self.machine_id.id, 'default_asset_id': self.asset_id.id},
        }
