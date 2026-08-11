from odoo import fields, models


class InheritedHrEmployee(models.Model):
    _inherit = 'hr.employee'

    letter_ids = fields.One2many('hr.employee.letters.history', 'employee_id', string="Letters")


class HrEmployeeLettersHistory(models.Model):
    """ Employee Emergency Contacts """
    _name = 'hr.employee.letters.history'
    _description = 'Employee Letters History'
    _rec_name = "employee_id"

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    # letter_name = fields.Char(string="Letter Name")
    letter_name = fields.Selection([
        ('confirmation_service', 'Confirmation of Service'),
        ('dismissal_letter', 'Dismissal Letter'),
        ('introduction_letter', 'Introduction Letter (LOI)'),
        ('demotion_letter', 'Letter of Demotion'),
        ('release_letter', 'Letter of Release & Certificate'),
        ('salary_refixation', 'Letter of Salary Re-Fixation'),
        ('offer_letter', 'Offer Letter'),
        ('termination_letter', 'Termination Letter'),
        ('transfer_letter', 'Transfer Letter'),
        ('visa_request_letter', 'Visa Request Letter'),
        ('warning_letter', 'Warning Letter'),
        ('resignation_acceptance', 'Acceptance of Resignation and Charge Handover'),
        ('charge_handover', 'Charge Handover And Transfer'),
        ('contract_letter', 'Contract Letter'),
        ('promotion_transfer', 'Promotion And Transfer')
    ], string='Letter Name')

    # contact_rel = fields.Char(string="Relation")
    letter_id = fields.Many2one('hr.employee.letters', string="Letter Reference")
