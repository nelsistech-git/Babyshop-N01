# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class FwPmSchedule(models.Model):
    _name = 'fw.pm.schedule'
    _description = 'Footwear Preventive Maintenance Schedule'
    _inherit = ['mail.thread']
    _order = 'next_due_date'

    name = fields.Char(string='Schedule Name', required=True)
    machine_id = fields.Many2one('fw.machine', string='Machine', required=True, tracking=True,
                                  ondelete='cascade')

    frequency_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Frequency', required=True, default='monthly')
    frequency_interval = fields.Integer(string='Repeat Every', default=1,
                                         help="E.g. 2 with Monthly frequency = every 2 months")

    last_maintenance_date = fields.Date(string='Last Maintenance Date')
    next_due_date = fields.Date(string='Next Due Date', required=True,
                                 default=fields.Date.context_today, tracking=True)

    responsible_id = fields.Many2one('hr.employee', string='Responsible Technician')
    checklist_ids = fields.One2many('fw.pm.schedule.checklist', 'schedule_id',
                                     string='Checklist Template')
    task_ids = fields.One2many('fw.pm.task', 'schedule_id', string='PM Tasks')
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count')

    active = fields.Boolean(default=True)

    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)

    def _get_next_date(self, from_date):
        self.ensure_one()
        interval = self.frequency_interval or 1
        if self.frequency_type == 'daily':
            return from_date + relativedelta(days=interval)
        if self.frequency_type == 'weekly':
            return from_date + relativedelta(weeks=interval)
        if self.frequency_type == 'monthly':
            return from_date + relativedelta(months=interval)
        if self.frequency_type == 'quarterly':
            return from_date + relativedelta(months=3 * interval)
        if self.frequency_type == 'yearly':
            return from_date + relativedelta(years=interval)
        return from_date

    def action_generate_task(self):
        """Manually generate the next PM Task work order for this schedule."""
        for rec in self:
            checklist_vals = [(0, 0, {
                'description': line.task_description,
                'sequence': line.sequence,
            }) for line in rec.checklist_ids]
            self.env['fw.pm.task'].create({
                'schedule_id': rec.id,
                'machine_id': rec.machine_id.id,
                'planned_date': rec.next_due_date,
                'technician_id': rec.responsible_id.id,
                'checklist_result_ids': checklist_vals,
            })

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PM Tasks',
            'res_model': 'fw.pm.task',
            'view_mode': 'tree,form',
            'domain': [('schedule_id', '=', self.id)],
        }


class FwPmScheduleChecklist(models.Model):
    _name = 'fw.pm.schedule.checklist'
    _description = 'PM Schedule Checklist Template Line'
    _order = 'sequence, id'

    schedule_id = fields.Many2one('fw.pm.schedule', string='PM Schedule', required=True,
                                   ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    task_description = fields.Char(string='Task Description', required=True)


class FwPmTask(models.Model):
    _name = 'fw.pm.task'
    _description = 'Footwear Preventive Maintenance Task (Work Order)'
    _inherit = ['mail.thread']
    _order = 'planned_date desc'

    name = fields.Char(string='PM Task Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.pm.task') or 'New')
    schedule_id = fields.Many2one('fw.pm.schedule', string='PM Schedule', ondelete='cascade')
    machine_id = fields.Many2one('fw.machine', string='Machine', required=True, tracking=True)

    planned_date = fields.Date(string='Planned Date', required=True,
                                default=fields.Date.context_today)
    actual_date = fields.Date(string='Actual Completion Date')
    technician_id = fields.Many2one('hr.employee', string='Technician')

    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True)

    checklist_result_ids = fields.One2many('fw.pm.task.checklist', 'task_id',
                                            string='Checklist Results')
    remarks = fields.Text(string='Remarks')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.pm.task') or 'New'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})
        self.mapped('machine_id').write({'status': 'under_maintenance'})

    def action_complete(self):
        for rec in self:
            today = fields.Date.context_today(rec)
            rec.write({'state': 'done', 'actual_date': today})
            rec.machine_id.write({'status': 'running'})
            if rec.schedule_id:
                next_due = rec.schedule_id._get_next_date(today)
                rec.schedule_id.write({
                    'last_maintenance_date': today,
                    'next_due_date': next_due,
                })

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class FwPmTaskChecklist(models.Model):
    _name = 'fw.pm.task.checklist'
    _description = 'PM Task Checklist Result Line'
    _order = 'sequence, id'

    task_id = fields.Many2one('fw.pm.task', string='PM Task', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Char(string='Task Description', required=True)
    is_done = fields.Boolean(string='Done')
    remarks = fields.Char(string='Remarks')
