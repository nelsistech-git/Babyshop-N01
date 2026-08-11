from odoo import api, fields, models
from odoo.addons.helper import validator


class PostCode(models.Model):
    _name = "postcode"
    _description = "PostCode"
    _order = 'name asc'

    name = fields.Char(string="Name", required=True, size=100, help="Name can be maximum 100 characters")
    thana_id = fields.Many2one("district.thana", string="Thana")
    district_id = fields.Many2one("district", string="District")
    division_id = fields.Many2one("division", string="Division")
    country_id = fields.Many2one("res.country", string="Country")

    @api.onchange('country_id')
    def _onchange_country(self):
        self.division_id = False

    @api.onchange('division_id')
    def _onchange_division(self):
        self.district_id = False

    @api.onchange('district_id')
    def _onchange_district(self):
        self.thana_id = False

    @api.onchange('thana_id')
    def _onchange_thana(self):
        self.name = False

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Post Code of the Thana"
        envObj = self.env['postcode']
        conditionList = [('country_id', '=', self.country_id.id), ('division_id', '=', self.division_id.id),
                         ('district_id', '=', self.district_id.id), ('thana_id', '=', self.thana_id.id),
                         ('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
