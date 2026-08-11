from odoo import api, exceptions, fields, models, _
from odoo.addons.helper import validator


class InheritResCompanyCommon(models.Model):
    _inherit = "res.company"
    _description = "Inherited Res Company Inherit Custom Stock"
    
    short_code = fields.Char(string="Short Code",size=10)
    
    @api.onchange("short_code")
    def _onchange_short_code(self):
        if self.short_code:
            self.short_code = str(self.short_code).strip().upper()
            
    @api.constrains('short_code')
    def _check_unique_constraint_short_code(self):
        msg = 'Company Code "%s"' % self.short_code
        envobj = self.env['res.company']
        conditionlist = [('name', '=', self.short_code)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)     