from odoo import models, fields


class InheritedResCompanyInheritCustomCommonSettings(models.Model):
    _inherit = "res.company"
    _description = "Inherited Res Company Inherit Custom Common Settings"

    cpf_type = fields.Selection([
        ('cpf_pf', 'CPF(%) of PF'),
        ('cpf_basic', 'CPF(%) of Basic'),
        ('cpf_gross', 'CPF(%) of Gross')
    ], string='CPF Type', default='cpf_pf')
    cpf_percentage = fields.Float(string='CPF (%)', default='0.00')

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    display_year = fields.Integer(string='Display Year', default=10)
    bin_no = fields.Char(string='BIN No.')
