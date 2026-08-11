# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PfProvidentBoard(models.Model):
    _name = "pf.provident.board"
    _inherit = 'mail.thread'
    _description = "Employee PF assign board"

    ## SELECTION ##
    state_selection = [('draft', 'Draft'), ('confirm', 'Confirm')]
    salary_selection = [('basic', 'Basic'), ('gross', 'Gross')]
    eligibility_selection = [('membership_date', 'Membership Date'), ('joining_date', 'Joining Date')]
    emp_type_list = [('management', 'Management'), ('staff', 'Staff')]

    ## ENDS HERE ##

    employee_lines = fields.One2many(comodel_name='pf.provident.board.line', inverse_name='pf_board_id',
                                     string='Employee Lines')
    state = fields.Selection(string="Status", selection=state_selection, default="draft", readonly=True, copy=False,
                             tracking=True)

    type = fields.Selection([('pf', 'PF'), ('wppf', 'WPPF')], string='Type', default='pf', required=True)

    name = fields.Char(string="Name", required=True, index=True)
    emp_type = fields.Selection(selection=emp_type_list, string='Employee Type',
                                tracking=True)

    pf_percentage = fields.Float('PF Percentage (%)', tracking=True, default=0)
    percentage_based_on = fields.Selection(selection=salary_selection, default='basic', string='Percentage Based On',
                                           tracking=True)
    pf_loan_policy = fields.Many2one(comodel_name="pf.loan.policy", string='Loan Policy', tracking=True)

    pf_config = fields.Many2one(comodel_name="pf.configuration", string='PF Configuration', tracking=True)
    forfeiture = fields.Float(string='Forfeiture Amount', compute='_compute_forfeiture_amount', readonly=True)
    forfeiture_interest = fields.Float(string='Profit Amount', compute='_compute_forfeiture_amount', readonly=True)
    total_forfeiture = fields.Float(string='Total Amount', compute='_compute_forfeiture_amount', readonly=True)
    coa_lines = fields.One2many(comodel_name='pf.coa.line', inverse_name='pf_board_id', string='COA Lines',
                                required=True)
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)

    def create_pf_profile(self):
        super(PfProvidentBoard, self).create_pf_profile()
        pf_profile = self.env['pf.profile'].sudo()
        for line in self.employee_lines:
            if not line.employee_id.is_pf_user:
                pf_profile.create({
                    'employee_id': line.employee_id.id,
                    'membership_date': line.start_date,
                    'pf_board_id': self.id,
                    'is_active': True,
                    'is_interest_free': line.is_interest_free
                })

    def _compute_forfeiture_amount(self):
        domain = [('is_disburse', '=', False), ('contribution_type', '=', 'debit')]
        for record in self:
            if record.id:
                domain.append(('pf_board_id', '=', record.id))
            forfeiture_contributions = self.env['pf.forfeiture.contribution'].search(domain)
            ff_comp_ff_amount = 0
            ff_interest_amount = 0
            for ff_cont in forfeiture_contributions:
                if ff_cont.contribution_source in ['company', 'forfeiture']:
                    ff_comp_ff_amount += ff_cont.balance
                elif ff_cont.contribution_source == 'interest':
                    ff_interest_amount += ff_cont.balance
            record.forfeiture = ff_comp_ff_amount
            record.forfeiture_interest = ff_interest_amount
            record.total_forfeiture = ff_comp_ff_amount + ff_interest_amount

    def button_confirm(self):
        for record in self:
            record.create_pf_profile()
            record.state = 'confirm'
        return

    def button_unlock(self):
        for record in self:
            record.state = 'draft'
        return

    @api.onchange('pf_percentage')
    def _onchange_pf_percent(self):
        for record in self:
            if record.pf_percentage and record.pf_percentage > 100:
                record.pf_percentage = 0
                return UserError(message=_("Max percentage can not be grater than 100."), title=_("Data Error"))


class PfPFLine(models.Model):
    _name = 'pf.provident.board.line'
    _description = 'Assign Employees to PF'

    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Provident Board Ref", index=True,
                                  ondelete='cascade')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True, related="pf_board_id.company_id",
                                 store=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    start_date = fields.Date('Start Date', required=True)
    is_interest_free = fields.Boolean(string='Is Profit Free', default=False)

    @api.onchange('company_id', 'pf_board_id.emp_type')
    def onchange_company_id(self):
        if self.pf_board_id.company_id and self.pf_board_id.emp_type:
            return {'domain': {'employee_id': [('company_id', '=', self.pf_board_id.company_id.id),
                                               ('is_pf_user', '=', False),
                                               ('emp_type', '=', self.pf_board_id.emp_type)]
                               }
                    }


class PfCOALine(models.Model):
    _name = 'pf.coa.line'
    _description = 'Chart of Accounts Line'

    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Provident Board Ref", index=True,
                                  ondelete='cascade')
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    # coa_id = fields.Many2one(comodel_name='pf.coa.config', string='Account')
    is_debit = fields.Boolean(string='Debit')
    is_credit = fields.Boolean(string='Credit')
