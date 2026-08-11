from odoo import api, fields, models
from odoo.addons.helper import validator


class CompanyUnit(models.Model):
    _name = "company.unit"
    _description = "Company Unit"

    name = fields.Char(string="Name", required=True, size=100, help="Name can be maximum 100 characters")
    company_id = fields.Many2one("res.company", string="Company", required=True)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.name = False

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Name of the Company"
        envObj = self.env['company.unit']
        conditionList = [('company_id', '=', self.company_id.id), ('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
