# coding=utf-8
from odoo import api, fields, models
from odoo.addons.helper import validator

class Zone(models.Model):
    """ Area/Territory Model """
    _name = "store.zone"
    _description = "Store Zone"
    
    name = fields.Char(string="Territory Name", required=True, size=100, help="Name can be maximum 100 characters")
    code = fields.Char(string="Territory Code", required=True, size=100, help="Code can be maximum 100 characters")
    manager_id = fields.Many2one('res.users', string="Manager Name", help='Manager of this Territory')
    # todo have to set manager_id dynamically on change of territory_id in res_users
    active = fields.Boolean(default=True)
    
    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()
            
    @api.constrains('name')
    def _check_unique_constraint(self):        
        msg = "name"
        envobj = self.env['store.zone']
        conditionlist = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
