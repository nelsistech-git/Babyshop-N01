from odoo import fields, models, api, _


class EmployeeBonusPayslipWizard(models.TransientModel):
    _name = 'employee.bonus.payslip.wizard'
    _description = 'Employee Bonus Payslip Wizard'

    bonus_id = fields.Many2one('hr.employee.bonus', 'Employee Bonus', ondelete="restrict")
    bonus_type_id = fields.Many2one('hr.employee.bonus.type', 'Bonus Type', related="bonus_id.bonus_type_id")
    date = fields.Date('Bonus Date', related="bonus_id.date")
    bonus_amount = fields.Float('Bonus Amount', related="bonus_id.bonus_amount")
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type")

    @api.model
    def default_get(self, fields):
        res = super(EmployeeBonusPayslipWizard, self).default_get(fields)
        batch_obj = self.env['hr.employee.bonus'].browse(self.env.context.get('active_id'))
        res['bonus_id'] = batch_obj.id
        return res

    def generate_bonus_payslip(self):
        self.ensure_one()
        self.bonus_id.action_create_payslip(self.disbursement_type)


class BatchEmployeeBonusPayslipWizard(models.TransientModel):
    _name = 'batch.employee.bonus.payslip.wizard'
    _description = 'Batch Employee Bonus Payslip Wizard'

    batch_id = fields.Many2one('batch.hr.employee.bonus', 'Employee Bonus', ondelete="restrict")
    date = fields.Date('Bonus Date', related="batch_id.bonus_date")
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type")

    @api.model
    def default_get(self, fields):
        res = super(BatchEmployeeBonusPayslipWizard, self).default_get(fields)
        batch_obj = self.env['batch.hr.employee.bonus'].browse(self.env.context.get('active_id'))
        res['batch_id'] = batch_obj.id
        return res

    def generate_bonus_payslip(self):
        for rec in self.batch_id.emp_bonus_ids:
            if not rec.payslip_id:
                rec.action_create_payslip(self.disbursement_type)

        self.batch_id.is_emp_bonus_done = True
        self.batch_id.state = 'done'
