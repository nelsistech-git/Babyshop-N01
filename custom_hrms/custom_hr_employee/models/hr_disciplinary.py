from odoo import models, fields, _, api
from odoo.exceptions import UserError
from calendar import monthrange


class HrPunishments(models.Model):
    _name = "hr.punishments"
    _description = "Employee Punishments"
    _rec_name = 'employee_id'
    _order = 'seq_name desc'

    seq_name = fields.Char(string='Ref', copy=False, default=lambda self: _('New'))

    type_id = fields.Many2one('hr.employee.disciplinary.type', string='Disciplinary Type')
    allow_date_range = fields.Boolean(related='type_id.allow_date_range')
    allow_payslip = fields.Boolean(string='Allow Payslip?')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', copy=False)
    employee_id = fields.Many2one('hr.employee', store=True)
    company_id = fields.Many2one('res.company', 'Company', store="True")
    department_id = fields.Many2one('hr.department', 'Department')
    pDate = fields.Datetime(string='Date Requested', default=fields.Datetime.now, readonly=True)
    amount = fields.Float(string='Punishment Amount')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    note = fields.Text(string='Note')
    old_empid = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                            domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    payslip_date = fields.Date(string='Payslip Date')

    initial_employment_date = fields.Date(string='Date of Joining')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete="restrict")
    gross_salary = fields.Float(string="Gross Salary")
    basic_salary = fields.Monetary(string="Basic Salary")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)

    no_of_calendar_days = fields.Integer(string="No. of Total Days", default=0, help="")
    disciplinary_days = fields.Integer(string="Action Days", default=0, help="")
    per_day_salary = fields.Float(string="Per Day Salary", digits=(16, 2))
    disciplinary_days_amt = fields.Float(string="Action Days Amount")

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only Draft record can be deleted!.'))

    type_of = fields.Selection([
        ('financial', 'Financial'),
        ('suspend', 'Suspend'),
        ('showcase', 'Pending'),
        ('Show_Cause', 'Show Cause'),
        ('warning', 'Warning'),
    ], string='Type')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.company_id = record.employee_id.company_id
                record.user_work_location_id = record.employee_id.user_work_location_id
                record.department_id = record.employee_id.department_id

                record.initial_employment_date = record.employee_id.initial_employment_date
                record.contract_id = record.employee_id.contract_id
                record.gross_salary = record.employee_id.contract_id.gross_salary or record.employee_id.contract_id.wage
                record.basic_salary = record.employee_id.contract_id.wage

                self._onchange_date_range()

    @api.onchange('from_date', 'to_date')
    def _onchange_date_range(self):
        for record in self:
            if record.employee_id and record.from_date and record.to_date:
                ndays = 0
                if record.to_date:
                    ndays = monthrange(record.to_date.year, record.to_date.month)[1]
                record.no_of_calendar_days = ndays

                disciplinary_days = 0
                if record.from_date and record.to_date:
                    disciplinary_days = (record.to_date - record.from_date).days + 1

                record.disciplinary_days = disciplinary_days

                record.per_day_salary = round(record.gross_salary / record.no_of_calendar_days, 2)
                record.disciplinary_days_amt = round(record.per_day_salary * disciplinary_days, 2)

    @api.onchange('type_id')
    def _onchange_type_id(self):
        for record in self:
            if record.type_id:
                record.allow_payslip = record.type_id.allow_payslip

    @api.onchange('amount')
    def _onchange_amount(self):
        for record in self:
            if record.amount < 0:
                record.amount = 0

    @api.depends('employee_id')
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.employee_id.name))
        return result

    @api.constrains('from_date', 'to_date')
    def _check_validity_check_in_check_out(self):
        for records in self:
            if records.from_date and records.to_date:
                if records.to_date < records.from_date:
                    raise UserError(_('"To" time cannot be earlier than "From" time.'))

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self:
            if rec.allow_payslip and not rec.payslip_date:
                raise UserError(_('You Must Enter The Payslip Date'))

            if rec.allow_payslip and rec.amount <= 0:
                raise UserError(_('You Must Enter The Punishment Amount'))

            if not rec.allow_payslip:
                rec.payslip_date = False
                rec.amount = 0
            rec.seq_name = self.env['ir.sequence'].get('hr_punish_code')
            rec.state = 'confirm'

    def action_approve(self):
        self.state = 'approve'
