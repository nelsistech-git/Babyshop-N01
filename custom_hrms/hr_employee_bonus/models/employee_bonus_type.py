from odoo import models, fields, api


class HREmployeeBonusType(models.Model):
    _name = 'hr.employee.bonus.type'
    _description = 'Employee Bonus Types'
    _inherit = 'mail.thread'
    _order = 'name'

    name = fields.Char('Name', required=True, tracking=True)
    calculation_type = fields.Selection([('fixed', 'Fixed Amount'),
                                         ('percentage', 'Percentage')], 'Calculation Type', default='fixed',
                                        required=True,
                                        help="""Fixed Amount : Determined in the process
                                         Percentage : Percentage based on bonus settings
                                         """,
                                        tracking=True)  # ('days', 'Days'); from the selected salary rule/s Days : Days amount considering the day amount equals to the sum of the selected salary rule/s divided by the month days
    payroll_code = fields.Char('Payroll Code', required=True, default='BONUS', tracking=True)

    percentage_from_settings = fields.Boolean('Percentage from bonus settings?',
                                              help="Percentage calculation from bonus settings", tracking=True)

    settings_type = fields.Selection([
        ('serv_len', 'Based on Length of service'),
        ('emp_type', 'Based on Employee Type'),
        ('serv_len_emp_type', 'Based on Length of Service and Employee Type'),
    ], string='Settings Type', tracking=True)

    on_joining_date = fields.Boolean('Based on Service Length (Days)',
                                     help="Bonus settings based on service length (days)", tracking=True)
    is_allowed_probation = fields.Boolean('Allowed Probation Employees?', tracking=True)

    on_employee_type = fields.Boolean('Based on Employee Type/Category', help="Bonus settings based on employee type",
                                      tracking=True)
    allowed_employee_type_ids = fields.Many2many('hr.employee.type', string='Allowed Employee Type/Category',
                                                 tracking=True)

    based_on_type = fields.Selection([
        ('gross', 'Gross'),
        ('basic', 'Basic'),
    ], string='Based On', tracking=True)

    active = fields.Boolean('Active', default=True, tracking=True)

    bonus_setting_ids = fields.One2many('hr.bonus.settings', 'head_id', string='Bonus Settings', help='Settings')

    @api.onchange('calculation_type')
    def _onchange_calculation_type(self):
        if self.calculation_type and self.calculation_type != 'percentage':
            self.percentage_from_settings = False

    def toggle_active(self):
        # Archive and Unarchive the bonus type
        for rec in self:
            rec.active = not rec.active

    def name_get(self):
        # Modifying The Display Name To Be : Bonus Type Name (Calculation Type)
        res = []
        for rec in self:
            calculation_type_label = dict(self._fields['calculation_type'].selection).get(rec.calculation_type)
            res.append((rec.id, rec.name + ' (%s)' % calculation_type_label))
        return res
