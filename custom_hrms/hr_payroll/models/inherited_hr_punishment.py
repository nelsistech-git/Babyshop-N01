from odoo import fields, models
from odoo.exceptions import UserError

class HrPunishmentInheritedPayroll(models.Model):
    _inherit = 'hr.punishments'
    _description = 'Employee Punishments'
    
    is_deducted = fields.Boolean(string='Payslip Deducted?')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip Ref')
    
    def action_approve(self):        
        if self.allow_payslip:
            address = self.employee_id.address_home_id
            if not address.id:
                raise UserError('Define home address for the employee. i.e address under private information of the employee.')
                
            if self.amount <= 0:
                raise UserError('You must Enter the Action amount')
            
            payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                         ('state', '=', 'done'), ('date_from', '<=', self.payslip_date),
                                                         ('date_to', '>=', self.payslip_date)], limit=1)
            if payslip_obj:
                raise UserError("This month salary already calculated")
                
            self.state = 'approve'
        else:
            self.state = 'approve'
