# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateProject(models.Model):
    """A real estate development project (residential, commercial, mixed...).

    Sits below Land/Land Agreement (a project is developed on one primary
    land parcel, under one primary agreement) and above the physical
    Building > Block > Floor > Unit structure.
    """
    _name = 'real.estate.project'
    _description = 'Real Estate Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Project Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_name = fields.Char(string='Project Name', required=True, tracking=True)

    project_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed Use'),
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('shopping_mall', 'Shopping Mall'),
        ('office', 'Office'),
        ('industrial', 'Industrial'),
        ('land_development', 'Land Development'),
    ], string='Project Type', required=True, default='residential', tracking=True)

    project_manager_id = fields.Many2one('res.users', string='Project Manager', tracking=True)

    land_id = fields.Many2one('real.estate.land', string='Primary Land',
                               tracking=True, ondelete='restrict')
    land_agreement_id = fields.Many2one('real.estate.land.agreement',
                                         string='Primary Land Agreement',
                                         tracking=True, ondelete='restrict',
                                         domain="[('land_id', '=', land_id)]")

    location = fields.Char(string='Location')
    address = fields.Text(string='Address')

    start_date = fields.Date(string='Start Date', tracking=True)
    planned_completion_date = fields.Date(string='Planned Completion Date', tracking=True)
    actual_completion_date = fields.Date(string='Actual Completion Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('planning', 'Planning'),
        ('approved', 'Approved'),
        ('construction', 'Construction'),
        ('qc', 'QC'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Project Status', default='draft', tracking=True, required=True, copy=False)

    total_land_area = fields.Float(related='land_id.area', string='Total Land Area',
                                    readonly=True, store=False)
    construction_area = fields.Float(string='Construction Area', digits=(12, 2))
    saleable_area = fields.Float(string='Saleable Area', digits=(12, 2))

    building_ids = fields.One2many('real.estate.building', 'project_id', string='Buildings')
    building_count = fields.Integer(compute='_compute_structure_counts', string='Buildings')
    unit_ids = fields.One2many('real.estate.unit', 'project_id', string='Units')
    unit_count = fields.Integer(compute='_compute_structure_counts', string='Units')
    unit_available_count = fields.Integer(compute='_compute_structure_counts', string='Available Units')
    unit_sold_count = fields.Integer(compute='_compute_structure_counts', string='Sold Units')

    budget_ids = fields.One2many('real.estate.project.budget', 'project_id', string='Budgets')
    budget_count = fields.Integer(compute='_compute_construction_counts')
    work_package_ids = fields.One2many('real.estate.work.package', 'project_id', string='Work Packages')
    work_package_count = fields.Integer(compute='_compute_construction_counts')
    boq_ids = fields.One2many('real.estate.boq', 'project_id', string='BOQs')
    boq_count = fields.Integer(compute='_compute_construction_counts')
    requisition_ids = fields.One2many('real.estate.requisition', 'project_id', string='Requisitions')
    requisition_count = fields.Integer(compute='_compute_construction_counts')
    site_report_ids = fields.One2many('real.estate.site.report', 'project_id', string='Site Reports')
    site_report_count = fields.Integer(compute='_compute_construction_counts')

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', copy=False,
        help='Cost center used to trace all project-related costs.')

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True)

    description = fields.Html(string='Description')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_project_ir_attachment_rel',
        'project_id', 'attachment_id', string='Documents')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Project Number must be unique per company.'),
    ]

    @api.depends('building_ids', 'unit_ids.status')
    def _compute_structure_counts(self):
        for rec in self:
            rec.building_count = len(rec.building_ids)
            rec.unit_count = len(rec.unit_ids)
            rec.unit_available_count = len(rec.unit_ids.filtered(lambda u: u.status == 'available'))
            rec.unit_sold_count = len(rec.unit_ids.filtered(lambda u: u.status == 'sold'))

    @api.depends('budget_ids', 'work_package_ids', 'boq_ids', 'requisition_ids', 'site_report_ids')
    def _compute_construction_counts(self):
        for rec in self:
            rec.budget_count = len(rec.budget_ids)
            rec.work_package_count = len(rec.work_package_ids)
            rec.boq_count = len(rec.boq_ids)
            rec.requisition_count = len(rec.requisition_ids)
            rec.site_report_count = len(rec.site_report_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.project') or 'New'
        return super().create(vals_list)

    @api.constrains('start_date', 'planned_completion_date', 'actual_completion_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.planned_completion_date and \
                    rec.planned_completion_date < rec.start_date:
                raise ValidationError(
                    'Planned Completion Date cannot be before Start Date for '
                    'project "%s".' % rec.project_name)
            if rec.start_date and rec.actual_completion_date and \
                    rec.actual_completion_date < rec.start_date:
                raise ValidationError(
                    'Actual Completion Date cannot be before Start Date for '
                    'project "%s".' % rec.project_name)

    def _require_state(self, expected_states):
        if isinstance(expected_states, str):
            expected_states = [expected_states]
        for rec in self:
            if rec.state not in expected_states:
                raise UserError(
                    'Action not allowed. Project "%s" must be in one of the '
                    'states %s (currently "%s").' % (
                        rec.project_name, expected_states, rec.state))

    def action_start_planning(self):
        self._require_state('draft')
        self.write({'state': 'planning'})

    def action_approve(self):
        self._require_state('planning')
        self.write({'state': 'approved'})

    def action_start_construction(self):
        self._require_state('approved')
        self.write({'state': 'construction'})

    def action_move_to_qc(self):
        self._require_state('construction')
        self.write({'state': 'qc'})

    def action_mark_ready(self):
        self._require_state('qc')
        self.write({'state': 'ready'})

    def action_complete(self):
        self._require_state('ready')
        self.write({'state': 'completed', 'actual_completion_date': fields.Date.context_today(self)})

    def action_close(self):
        self._require_state('completed')
        self.write({'state': 'closed'})

    def action_cancel(self):
        self._require_state(['draft', 'planning', 'approved'])
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_view_buildings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buildings',
            'res_model': 'real.estate.building',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_units(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Units',
            'res_model': 'real.estate.unit',
            'view_mode': 'kanban,tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_budgets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budgets',
            'res_model': 'real.estate.project.budget',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_work_packages(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Packages',
            'res_model': 'real.estate.work.package',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_boqs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'BOQ',
            'res_model': 'real.estate.boq',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Requisitions',
            'res_model': 'real.estate.requisition',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_site_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Reports',
            'res_model': 'real.estate.site.report',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
