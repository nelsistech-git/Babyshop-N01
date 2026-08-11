from odoo import api, fields, models
from odoo.addons.helper import validator


class DistrictThana(models.Model):
    _name = "district.thana"
    _description = "District Upazila/Thana"
    _order = 'name asc'

    name = fields.Char(string="Upazila/Thana", required=True, size=100,
                       help="Name can be maximum 100 characters")
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
        self.name = False

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Upazila name of the district of the division"
        envObj = self.env['district.thana']
        conditionList = [('country_id', '=', self.country_id.id), ('division_id', '=', self.division_id.id),
                         ('district_id', '=', self.district_id.id),
                         ('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
