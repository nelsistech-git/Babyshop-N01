from odoo import models, fields, api
from odoo.addons.helper import validator


class UoM(models.Model):
    _inherit = "uom.uom"

    uom_code = fields.Char(size=20, string='UoM Code', copy=False, help="Code can be maximum 20 characters")

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        for rec in self:
            msg = 'Unit of measure "%s"' % rec.name
            envobj = self.env['uom.uom']
            conditionlist = [('name', '=ilike', rec.name)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
