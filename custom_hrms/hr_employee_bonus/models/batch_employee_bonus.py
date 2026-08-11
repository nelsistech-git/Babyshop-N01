from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
from odoo import fields, models, api, _


class BatchHREmployeeBonus(models.Model):
    _name = 'batch.hr.employee.bonus'
    _description = 'Batch Employee Bonus'
    _order = 'bonus_date desc'

    def _get_bonus_type(self):
        return self.env['hr.employee.bonus.type'].search([], limit=1, order='id ASC')

    name = fields.Char()
    emp_bonus_ids = fields.One2many('hr.employee.bonus', 'batch_emp_bonus_id', string='Employee Bonus', readonly=True)

    bonus_date = fields.Date(string='Bonus Date', required=True, readonly=True,
                             default=lambda self: fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
                                 default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')

    bonus_type_id = fields.Many2one('hr.employee.bonus.type', 'Bonus Type', default=_get_bonus_type)
    calculation_type = fields.Selection(related='bonus_type_id.calculation_type', string='Calculation Type')
    percentage_from_settings = fields.Boolean('Percentage from settings?',
                                              related='bonus_type_id.percentage_from_settings')
    settings_type = fields.Selection(string='Settings Type', related='bonus_type_id.settings_type')
    allowed_employee_type_ids = fields.Many2many('hr.employee.type', related='bonus_type_id.allowed_employee_type_ids',
                                                 string='Allowed Employee Type/Category')

    bonus_on_joining_date = fields.Boolean(related='bonus_type_id.on_joining_date',
                                           string='Bonus on Joining Date')  # not used
    on_employee_type = fields.Boolean(related='bonus_type_id.on_employee_type',
                                      string='Bonus on employee type')  # not used

    amount_percentage = fields.Float(help="""
    In case of fixed amount, bonus amount = Amount * Quantity
    In case of percentage, bonus amount = (based on settings amount) * Quantity
    """)
    emp_bonus_count = fields.Integer(compute='_compute_emp_bonus_count')

    based_on_type = fields.Selection(string='Based On', related='bonus_type_id.based_on_type')

    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('done', 'Payslip Done'),
                              ('cancelled', 'Cancelled')], string='Status', index=True, readonly=True, copy=False,
                             default='draft')

    is_emp_bonus_done = fields.Boolean(string='Payslip Created')

    @api.onchange('user_work_location_id', 'bonus_date', 'bonus_type_id')
    def _onchange_employee(self):
        self.name = 'Batch %s Bonus: %s - %s' % (self.user_work_location_id.display_name or '', self.bonus_type_id.name,
                                                 format_date(self.env,
                                                             self.bonus_date,
                                                             date_format="MMMM y"))

    @api.onchange('amount_percentage')
    def _onchange_amount_negative_check(self):
        for rec in self:
            if rec.amount_percentage < 0:
                raise ValidationError("Value cannot be negative value")

    def unlink(self):
        if any(self.filtered(lambda att: att.state not in ('draft'))):
            raise UserError(_('Only draft record allowed to delete!'))
        return super(BatchHREmployeeBonus, self).unlink()

    def _compute_emp_bonus_count(self):
        for rec in self:
            rec.emp_bonus_count = len(self.emp_bonus_ids)

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_emp_bonus_done(self):
        for rec in self.emp_bonus_ids:
            if not rec.payslip_id:
                rec.action_create_payslip()
        self.is_emp_bonus_done = True
        self.state = 'done'

    def action_confirm(self):
        for rec in self.emp_bonus_ids:
            rec.action_confirm()
        self.write({'state': 'confirmed'})

    def action_open_emp_bonus_sheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.employee.bonus",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.emp_bonus_ids.ids]],
            "name": "Employee Bonus",
        }
