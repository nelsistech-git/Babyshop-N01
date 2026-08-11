from odoo import models, fields


class ReportColorSettings(models.Model):
    _name = "report.color.settings"
    _description = "Report Color Settings"

    report_name = fields.Selection([
        ('01', 'Payslip'),
        ('02', 'Employee Salary Sheet'),
    ], string='Report Name', required=True)
    color1 = fields.Char('Color-01', default='#FFFFFF')
    color2 = fields.Char('Color-02', default='#FFFFFF')
    color3 = fields.Char('Color-03', default='#FFFFFF')
    note = fields.Char('Note')
