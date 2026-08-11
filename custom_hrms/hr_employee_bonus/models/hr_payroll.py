from odoo import models, api


class HRPayslipInheritHrBonus(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = super(HRPayslipInheritHrBonus, self).get_inputs(contracts, date_from, date_to)
        for contract in contracts:
            if date_from and date_to:
                employee_bonuses = self.env['hr.employee.bonus'].search([('employee_id', '=', contract.employee_id.id),
                                                                         ('date', '>=', date_from),
                                                                         ('date', '<=', date_to),
                                                                         ('state', '=', 'confirmed')])
                if employee_bonuses:
                    for rec in employee_bonuses:
                        payroll_code = rec.bonus_type_id.payroll_code
                        bonus_amount = rec.bonus_amount
                        for result in res:
                            if result.get('code') == payroll_code:
                                total_bonus_amt = result.get('amount') or 0
                                result['amount'] = total_bonus_amt + bonus_amount

        return res

    def action_payslip_done(self):
        res = super(HRPayslipInheritHrBonus, self).action_payslip_done()
        if self.employee_id:
            employee_id = self.employee_id.id
            date_from = self.date_from
            date_to = self.date_to
            input_lines = self.input_line_ids

            payroll_codes = [line.code for line in input_lines if line.amount > 0]

            bonus_rows = self.env['hr.employee.bonus'].sudo().search(
                [('employee_id', '=', employee_id),
                 ('date', '>=', date_from),
                 ('date', '<=', date_to),
                 ('state', '=', 'confirmed'),
                 ('bonus_type_id.payroll_code', 'in', payroll_codes)])

            for rec in bonus_rows:
                rec.state = 'paid'
                rec.payslip_id = self.id
