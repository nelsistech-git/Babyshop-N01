from odoo import fields, models


class LoanRejectReason(models.TransientModel):
    _name = "loan.reject.reason"
    _description = "Loan Reject Reason"

    reason = fields.Text('Reason', required=True)

    def reject_loan(self):
        active_ids = self._context.get('active_ids')
        loan_ids = self.env['employee.loan'].browse(active_ids)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

        for loan in loan_ids:
            if loan.state == 'request':
                loan.state = 'reject'
                loan.reject_reason = self.reason
            elif loan.state == 'dep_approval':
                loan.state = 'reject'
                loan.reject_reason_hr = self.reason
                loan.hr_manager_id = employee_id and employee_id.id or False
            elif loan.state == 'hr_approval':
                loan.state = 'reject'
                loan.reject_reason_acc = self.reason
                loan.acc_manager_id = employee_id and employee_id.id or False
            elif loan.state == 'acc_approval':
                loan.state = 'reject'
                loan.reject_reason_trusty = self.reason
                loan.trusty_manager_id = employee_id and employee_id.id or False

        return True


class SkipInstallmentRejectReason(models.TransientModel):
    _name = "skip.installment.reject.reason"
    _description = "Skip Installment Reject Reason"

    reason = fields.Text('Reason', required=True)

    def reject_skip_installment(self):
        active_ids = self._context.get('active_ids')
        installment_ids = self.env['dev.skip.installment'].browse(active_ids)
        for installment in installment_ids:
            installment.reject_reason = self.reason
            if installment.state == 'request':
                installment.dep_reject_skip_installment()
            if installment.state == 'approve':
                installment.hr_reject_skip_installment()
        return True
