from odoo import models


class HrPayslipInheritHrAdvance(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip.
                           """
        res = super(HrPayslipInheritHrAdvance, self).get_inputs(contract_ids, date_from, date_to)
        contract_obj = self.env['hr.contract']
        emp_id = contract_obj.browse(contract_ids[0].id).employee_id
        adv_salary = self.env['salary.advance'].search([('employee_id', '=', emp_id.id),
                                                        ('payslip_date', '>=', date_from),
                                                        ('payslip_date', '<=', date_to),
                                                        ('state', '=', 'approve'),
                                                        ('advance', '>', 0),
                                                        ('is_deducted', '=', False)])

        for adv_obj in adv_salary:
            adv_amount = adv_obj.advance
            for result in res:
                if result.get('code') == 'SAR':
                    total_adv_amt = result.get('amount') or 0
                    result['amount'] = total_adv_amt + adv_amount

        return res

    def action_payslip_done(self):
        res = super(HrPayslipInheritHrAdvance, self).action_payslip_done()
        if self.employee_id:
            employee_id = self.employee_id.id
            date_from = self.date_from
            date_to = self.date_to
            input_lines = self.input_line_ids

            payroll_codes = [line.code for line in input_lines if line.code == 'SAR' and line.amount > 0]
            if len(payroll_codes) > 0:
                advance_rows = self.env['salary.advance'].search([
                    ('employee_id', '=', employee_id),
                    ('payslip_date', '>=', date_from),
                    ('payslip_date', '<=', date_to),
                    ('state', '=', 'approve'),
                    ('advance', '>', 0),
                    ('is_deducted', '=', False)
                ])

                for rec in advance_rows:
                    rec.is_deducted = True
                    rec.payslip_id = self.id
