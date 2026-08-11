from odoo import models, fields, api


class InstallmentLine(models.Model):
    _name = 'installment.line'
    _description = 'Installment Line'
    _order = 'date,name'

    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    loan_id = fields.Many2one('employee.loan', string='Loan', required=True, ondelete='cascade')
    date = fields.Date('Date')
    is_paid = fields.Boolean('Paid')
    paid_date = fields.Date('Paid Date')
    amount = fields.Float('Loan Amount')
    interest = fields.Float('Total Interest')
    ins_interest = fields.Float('Interest Amount')
    installment_amt = fields.Float('EMI (Inst.) Amount')
    total_installment = fields.Float('Total', compute='get_total_installment')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    is_skip = fields.Boolean('Skip EMI (Inst.)')
    is_early_settlement = fields.Boolean('Early Settlement')
    is_remission = fields.Boolean('Remission')
    move_id = fields.Many2one('account.move', string='Journal')


    @api.depends('installment_amt', 'ins_interest')
    def get_total_installment(self):
        for line in self:
            line.total_installment = line.ins_interest + line.installment_amt

    def send_paid_mail(self):
        if self.employee_id and self.employee_id.work_email:
            template_id = self.env['ir.model.data']._xmlid_lookup('dev_hr_loan.dev_employee_installment_paid_send_mail')

            template_id = self.env['mail.template'].browse(template_id[1])
            template_id.send_mail(self.ids[0], True)
        return True

    def action_view_payslip(self):
        if self.payslip_id:
            return {
                'view_mode': 'form',
                'res_id': self.payslip_id.id,
                'res_model': 'hr.payslip',
                'view_type': 'form',
                'type': 'ir.actions.act_window'
            }

    def view_journal_entry(self):
        if self.move_id:
            return {
                'view_mode': 'form',
                'res_id': self.move_id.id,
                'res_model': 'account.move',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': {'default_type': 'entry'}
            }
