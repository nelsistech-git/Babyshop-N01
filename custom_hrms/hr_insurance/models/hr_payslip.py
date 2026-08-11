from odoo import models


class HrPayslip(models.Model):
    """inherited to add fields"""
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """used get inputs , to add datas"""
        res = super().get_inputs(contract_ids, date_from, date_to)
        contract_obj = self.env['hr.contract']
        for record in contract_ids:
            if contract_ids[0]:
                emp_id = contract_obj.browse(record[0].id).employee_id
                for result in res:
                    if emp_id.deduced_amount_per_month != 0:
                        if result.get('code') == 'INSUR':
                            result['amount'] = emp_id.deduced_amount_per_month
        return res