from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.addons.helper import validator
from datetime import date


class HREmployeeBonus(models.Model):
    _name = 'hr.employee.bonus'
    _description = 'Employee Bonuses'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'
    _order = 'date desc, employee_id asc'

    # name = fields.Char('Description')
    bonus_type_id = fields.Many2one('hr.employee.bonus.type', 'Bonus Type', ondelete="restrict")
    date = fields.Date('Bonus Date', default=fields.Date.context_today)
    date_confirm = fields.Date('Confirmation Date')
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete="restrict")
    id_card_no = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID', related='employee_id.device_user_id')

    user_work_location_id = fields.Many2one(related='employee_id.user_work_location_id', string='Work/Job Location')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department',
                                    help='Employee Department')
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position', help='Employee Job Position')

    initial_employment_date = fields.Date(string='Date of Joining')
    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type', ondelete="restrict")
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete="restrict")
    gross_salary = fields.Float(string="Gross Salary")  # related='contract_id.gross_salary'
    basic_salary = fields.Monetary(string="Basic Salary")  # related='contract_id.wage'

    calculation_type = fields.Selection(related='bonus_type_id.calculation_type', string='Calculation Type')
    percentage_from_settings = fields.Boolean('Percentage from settings?',
                                              related='bonus_type_id.percentage_from_settings')
    settings_type = fields.Selection(string='Settings Type', related='bonus_type_id.settings_type')

    allowed_employee_type_ids = fields.Many2many('hr.employee.type', related='bonus_type_id.allowed_employee_type_ids',
                                                 string='Allowed Employee Type/Category')

    amount_percentage = fields.Float(string='Fixed Amount/(%)', help="""
    In case of fixed amount, bonus amount = Amount * Quantity
    In case of percentage, bonus amount = (based on settings amount) * Quantity
    """)  # (The sum of the salary rule/s amount * Percentage /100) * Quantity;    In Case of days, bonus amount = (Day Amount * Percentage /100) * Quantity
    quantity = fields.Float('Quantity', default=1)
    bonus_amount = fields.Float('Bonus Amount')  # Todo Add Currency Sign To The Amount
    note = fields.Text('Notes')

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('paid', 'Payslip Done'),
                              ('cancelled', 'Cancelled')], tracking=True, default='draft')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', ondelete="set null")
    batch_emp_bonus_id = fields.Many2one('batch.hr.employee.bonus', string='Batch Employee Bonus', ondelete="restrict")
    reference = fields.Char(string='References')
    based_on_type = fields.Selection([
        ('gross', 'Gross'),
        ('basic', 'Basic'),
    ], string='Based On')

    is_paid = fields.Boolean(string='Payment Paid?', related='payslip_id.is_paid')
    payment_date = fields.Date(string="Payment Date", related='payslip_id.payment_date')

    @api.onchange('amount_percentage', 'quantity')
    def _onchange_amount_negative_check(self):
        for rec in self:
            if rec.amount_percentage < 0:
                raise ValidationError("Value cannot be negative value")
            if rec.quantity < 0:
                raise ValidationError("Quantity cannot be negative value")

    def unlink(self):
        if any(self.filtered(lambda self: self.state not in ('draft'))):
            raise UserError(_('Only draft record allowed to delete!'))
        return super(HREmployeeBonus, self).unlink()

    @api.onchange('employee_id', 'date', 'bonus_type_id', 'quantity', 'amount_percentage')
    def _onchange_employee(self):
        # Calculate bonus amount and confirm the request
        if self.employee_id:
            self.initial_employment_date = self.employee_id.initial_employment_date
            self.employee_type_id = self.employee_id.employee_type_id
            self.contract_id = self.employee_id.contract_id
            self.gross_salary = self.employee_id.contract_id.gross_salary
            self.basic_salary = self.employee_id.contract_id.wage
            self.based_on_type = self.bonus_type_id.based_on_type
            self.settings_type = self.bonus_type_id.settings_type

            if not self.employee_id.contract_id:
                raise UserError(_('Please Make Sure The Selected Employee Has Valid Contract'))
            else:
                reference = ''
                if self.calculation_type == 'percentage':  # percentage calculation
                    joining_date = self.employee_id.initial_employment_date
                    bonus_date = self.date
                    based_on_type = self.bonus_type_id.based_on_type
                    percentage_from_settings = self.percentage_from_settings
                    if not percentage_from_settings:  # percentage but not from settings
                        amount_percentage = self.amount_percentage
                        if based_on_type == 'gross':
                            amount = self.employee_id.contract_id.gross_salary
                        else:
                            amount = self.employee_id.contract_id.wage

                        bonus_amount = amount * (amount_percentage / 100) * self.quantity

                    else:
                        settings_type = self.bonus_type_id.settings_type

                        try:
                            service_length_day = (bonus_date - joining_date).days
                        except:
                            service_length_day = 0

                        settings_domain = [('head_id', '=', self.bonus_type_id.id)]
                        if settings_type == 'emp_type':
                            settings_domain.append(('employee_type_id', '=', self.employee_type_id.id))
                        elif settings_type == 'serv_len':
                            settings_domain.append(('days_from', '<=', service_length_day))
                            settings_domain.append(('days_to', '>=', service_length_day))
                        elif settings_type == 'serv_len_emp_type':
                            settings_domain.append(('employee_type_id', '=', self.employee_type_id.id))
                            settings_domain.append(('days_from', '<=', service_length_day))
                            settings_domain.append(('days_to', '>=', service_length_day))
                        else:
                            raise UserError(_('Settings type not available of the Bonus type!'))

                        bonus_sett_row = self.env['hr.bonus.settings'].search(settings_domain, limit=1)
                        if not bonus_sett_row:
                            raise UserError(_('Bonus settings not available of the Bonus type!'))
                        else:
                            amount_percentage = bonus_sett_row[0].amount_percentage
                            based_on_type = bonus_sett_row[0].based_on_type
                            reference = '{0}'.format(bonus_sett_row[0].reference or '')

                            self.amount_percentage = amount_percentage
                            self.based_on_type = based_on_type

                            if based_on_type == 'gross':
                                amount = self.employee_id.contract_id.gross_salary
                            else:
                                amount = self.employee_id.contract_id.wage

                            bonus_amount = amount * (amount_percentage / 100) * self.quantity

                else:  # fixed calculation
                    amount_percentage = self.amount_percentage
                    bonus_amount = amount_percentage * self.quantity

                self.bonus_amount = round(bonus_amount, 0)
                self.reference = reference

    @api.constrains('employee_id', 'bonus_type_id', 'date')
    def _check_unique_employee_bonus(self):
        for rec in self:
            msg = '"{0}" given to "{1}" on "{2}"'.format(rec.bonus_type_id.name, rec.employee_id.name, rec.date)
            envobj = self.env['hr.employee.bonus']
            conditionlist = [('employee_id', '=', rec.employee_id.id), ('bonus_type_id', '=', rec.bonus_type_id.id),
                             ('date', '=', rec.date)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('bonus_type_id')
    def _bonus_type_id(self):
        if self.bonus_type_id:
            return {'domain': {'employee_id': [('employee_type_id', 'in', self.allowed_employee_type_ids.ids)]}}

    def action_confirm(self):
        if not self.employee_id.contract_id:
            raise UserError(_('Please Make Sure The Selected Employee Has Valid Contract'))
        date_today = date.today()
        if self.amount_percentage <= 0:
            raise ValidationError(_('Amount or Percentage must be greater than zero!'))
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be greater than zero!'))
        self.write({'state': 'confirmed', 'date_confirm': date_today})

    def action_cancel(self):
        if self.state == 'confirmed':
            self.state = 'cancelled'
        else:
            raise UserError(_('Sorry! Only Confirmed Requests Can Be Cancelled'))

    def action_draft(self):
        if self.state == 'cancelled':
            self.state = 'draft'
        else:
            raise UserError(_('Sorry! Only Cancelled Request Can Be Set To Draft'))

    def action_payslip(self):
        self.action_create_payslip()
        # self.write({'state': 'paid'})

    def action_create_payslip(self, disbursement_type=None):
        payslip_obj = self.env['hr.payslip']
        for rec in self:
            if rec.payslip_id:
                raise ValidationError(_('Payslip Has Been Created Before for %s') % rec.employee_id.name)

            contract_obj = rec.employee_id.contract_id or None
            if not contract_obj:
                raise ValidationError(_('Required Contract for %s') % rec.employee_id.name)
            else:
                pass

            if not contract_obj.bonus_struct_id:
                raise ValidationError(_('Required Bonus Structure in contract for %s') % rec.employee_id.name)
            else:
                bonus_struct_id = contract_obj.bonus_struct_id.id

            disbursement_type = disbursement_type or contract_obj.disbursement_type

            new_payslip = payslip_obj.new({
                'employee_id': rec.employee_id.id,
                'date_from': rec.date,
                'date_to': rec.date,
                'contract_id': contract_obj.id,
                'struct_id': bonus_struct_id,
                'disbursement_type': disbursement_type
            })
            new_payslip._onchange_employee()
            payslip_dict = new_payslip._convert_to_write({
                name: new_payslip[name] for name in new_payslip._cache})

            payslip_id = payslip_obj.create(payslip_dict)

            payslip_id.compute_sheet()
            payslip_id.action_payslip_done()
            rec.payslip_id = payslip_id
