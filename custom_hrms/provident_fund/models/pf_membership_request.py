# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError


class PfPFMembershipRequest(models.Model):
    _name = "pf.membership.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Can request for PF Membership"

    # SELECTION LIST
    state_selection = [
        ('draft', 'Draft'),
        ('apply', 'Apply'),
        ('approved', 'Approved'),
        ('cancel', 'Rejected')
    ]
    emp_type_list = [('management', 'Management'), ('worker', 'Worker'), ('staff', 'Staff')]
    # END HERE

    state = fields.Selection(selection=state_selection, string="Status", default="draft", readonly=True, tracking=True)
    name = fields.Char('Name', required=True, default=_('New'), readonly=True, copy=False, tracking=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee", required=True, tracking=True,
                                  copy=False)
    employee_uid = fields.Char(related='employee_id.id_card_no', readonly=True)
    employee_name = fields.Char(related="employee_id.name", string="Employee Name", readonly=True)
    job_id = fields.Many2one(comodel_name='hr.job', related="employee_id.job_id", string="Designation", readonly=True)
    emp_type = fields.Selection(string='Employee Type', related="employee_id.emp_type", readonly=True)

    tax_identification = fields.Char(string="TAX Identification", readonly=True)
    join_date = fields.Date(related="employee_id.initial_employment_date", string="Joining Date", readonly=True)
    date_apply = fields.Date(string="Apply Date", readonly=True, tracking=True)
    date_start = fields.Date(string="Start Date", required=True, tracking=True)
    pf_board_id = fields.Many2one(comodel_name='pf.provident.board', string="PF Board", domain="[('type', '=', 'pf')]")
    is_interest_free = fields.Boolean(string='Is Profit Free', default=False)
    is_manager = fields.Boolean(string='Is Manager', compute='_compute_is_manager', store=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.onchange('company_id', 'emp_type')
    def onchange_emp_type(self):
        if self.company_id and self.emp_type:
            return {'domain': {'pf_board_id': [('company_id', '=', self.company_id.id), ('type', '=', 'pf')]}}

    @api.depends('company_id')
    def _compute_is_manager(self):
        for rec in self:
            current_user = self.env.user
            rec.is_manager = (current_user.has_group(
                'provident_fund.group_provident_fund_manager') or current_user.id == SUPERUSER_ID)

    @api.model
    def default_get(self, fields_list):
        res = super(PfPFMembershipRequest, self).default_get(fields_list)
        current_user = self.env.user
        if current_user:
            res['employee_id'] = self.env.user.employee_id.id
        return res

    def action_apply(self):
        self.ensure_one()
        return self.write({'state': 'apply', 'date_apply': fields.Date.today()})

    def action_approve(self):
        self.ensure_one()
        if not (self.env.user.has_group('provident_fund.group_provident_fund_manager') or self.env.user.id != SUPERUSER_ID):
            raise UserError(msg=_("Only a Provident Fund Manager can approve/reject Allocation Request."),
                            title=_("Permission Error"))
        else:
            if self.pf_board_id:
                self.env['pf.provident.board.line'].create({
                    'employee_id': self.employee_id.id,
                    'company_id': self.company_id.id,
                    'pf_board_id': self.pf_board_id.id,
                    'start_date': self.date_start,
                    'is_interest_free': self.is_interest_free
                })
            self.env['pf.profile'].create({
                'employee_id': self.employee_id.id,
                'membership_date': self.date_start,
                'membership_approve_date': fields.Date.today(),
                'pf_percentage': self.pf_board_id.pf_percentage if self.pf_board_id else 0,
                'percentage_based_on': self.pf_board_id.percentage_based_on if self.pf_board_id else '',
                'pf_board_id': self.pf_board_id.id if self.pf_board_id else False,
                'is_active': True,
                'is_interest_free': self.is_interest_free
            })
            self.employee_id.is_pf_user = True
            self.employee_id.pf_start_date = self.date_start
            return self.write({'state': 'approved'})

    def action_apply_all(self):
        rows = self.sudo().search([('state', '=', 'draft')])
        today = fields.Date.today()
        for rec in rows:
            rec.state = 'apply'
            rec.date_apply = today

    def action_approve_all(self):
        rows = self.sudo().search([('state', '=', 'apply')])
        boar_line_obj = self.env['pf.provident.board.line']
        profile_obj = self.env['pf.profile']
        today = fields.Date.today()
        for rec in rows:
            if not rec.pf_board_id:
                raise UserError("Required PF Board of '%s'" % (rec.employee_id.name))
            else:
                boar_line_obj.sudo().create({
                    'employee_id': rec.employee_id.id,
                    'company_id': rec.company_id.id,
                    'pf_board_id': rec.pf_board_id.id,
                    'start_date': rec.date_start,
                    'is_interest_free': rec.is_interest_free
                })
            profile_obj.sudo().create({
                'employee_id': rec.employee_id.id,
                'membership_date': rec.date_start,
                'membership_approve_date': today,
                'pf_percentage': rec.pf_board_id.pf_percentage if rec.pf_board_id else 0,
                'percentage_based_on': rec.pf_board_id.percentage_based_on if rec.pf_board_id else '',
                'pf_board_id': rec.pf_board_id.id if rec.pf_board_id else False,
                'is_active': True,
                'is_interest_free': rec.is_interest_free
            })
            rec.employee_id.is_pf_user = True
            rec.employee_id.pf_start_date = rec.date_start

            rec.state = 'approved'

    def action_cancel(self):
        self.ensure_one()
        return self.write({'state': 'cancel'})

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if 'name' not in val or val['name'] == _('New'):
                sequence = self.env['ir.sequence'].next_by_code('pf.membership.request.code') or _('New')
                company_code = self.env.user.company_id.short_code.upper().strip()
                sequence = sequence.replace('{company_code}', company_code)
                val['name'] = sequence
        res = super(PfPFMembershipRequest, self).create(vals)
        return res

    def unlink(self):
        for record in self:
            if record.state == "approved":
                raise UserError(message="You can not delete any approved request.", title="Permission Error")
            super(PfPFMembershipRequest, record).unlink()
