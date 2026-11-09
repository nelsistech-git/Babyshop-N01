# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstateWorkPackage(models.Model):
    """A unit of construction work (e.g. Foundation, Column, Beam, Slab,
    Brick Work, Plaster, Finishing) that can optionally nest under a
    parent package to model a hierarchy such as
    Construction > Foundation > Column > Beam > Slab."""
    _name = 'real.estate.work.package'
    _description = 'Real Estate Work Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'work_name'
    _order = 'project_id, sequence, id'

    name = fields.Char(string='Work Code', copy=False, tracking=True,
                        default='New', readonly=True)
    work_name = fields.Char(string='Work Name', required=True, tracking=True)
    sequence = fields.Integer(default=10)

    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, ondelete='cascade', tracking=True)
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    parent_id = fields.Many2one('real.estate.work.package', string='Parent Work Package',
                                 domain="[('project_id', '=', project_id)]", ondelete='cascade')
    child_ids = fields.One2many('real.estate.work.package', 'parent_id', string='Sub Work Packages')

    contractor_id = fields.Many2one('real.estate.contractor', string='Contractor', tracking=True)

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    planned_quantity = fields.Float(string='Planned Quantity', digits=(12, 2))
    completed_quantity = fields.Float(string='Completed Quantity', digits=(12, 2))
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    rate = fields.Monetary(string='Rate')
    budget = fields.Monetary(string='Budget')
    actual_cost = fields.Monetary(string='Actual Cost', default=0.0)

    progress = fields.Float(string='Progress %', compute='_compute_progress', store=True, digits=(5, 2))

    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Work Code must be unique per company.'),
    ]

    @api.depends('planned_quantity', 'completed_quantity')
    def _compute_progress(self):
        for rec in self:
            rec.progress = rec.planned_quantity and min(
                100.0, (rec.completed_quantity / rec.planned_quantity) * 100.0) or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.work.package') or 'New'
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError('End Date cannot be before Start Date for '
                                       'work package "%s".' % rec.work_name)

    @api.constrains('parent_id')
    def _check_no_self_parent_loop(self):
        for rec in self:
            visited = set()
            node = rec.parent_id
            while node:
                if node.id in visited or node.id == rec.id:
                    raise ValidationError('Work Package hierarchy cannot contain a loop.')
                visited.add(node.id)
                node = node.parent_id

    def action_start(self):
        self.write({'status': 'in_progress'})

    def action_complete(self):
        self.write({'status': 'completed'})

    def action_hold(self):
        self.write({'status': 'on_hold'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})
