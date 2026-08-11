from odoo import api, exceptions, fields, models
from odoo.addons.helper import validator
#from odoo.addons.base_phone.fields import Phone, Fax

class GoDownOwnerDetails(models.Model):
    _name = 'godownowner.details'
    _description = "Go-down Details"
    
    name = fields.Char(string="Name", size=100)
    # phone = fields.Char(string="Contact Number",size=15)
    #phone = Phone(country_field='country_id', size=15)
    phone = fields.Char('Phone', tracking=50)
    
    godown_owner_address = fields.Text(string="Address", help="Address can be maximum 200 characters")
    email = fields.Char(string="Email", size=50)
    country_id = fields.Many2one("res.country", string="Country")
    godown_id = fields.Many2one("store.godown", string="Go down", ondelete="cascade")
    
    @api.onchange("name")
    def _onchange_name(self):
        if self.name:        
            self.name = str(self.name).strip()
    
    @api.constrains('email')
    def _check_email_validation(self):
        if self.email:
            msg = ""
            validator._validate_email(self, self.email, msg)
    
    @api.constrains('phone')
    def _check_phone_validation(self): 
        if self.phone:
            msg = "Phone Number "
            validator._valid_phone_number(self, self.phone, msg)
            
    @api.constrains('name')
    def _check_name_validation(self):
            if self.name == False:
                raise exceptions.ValidationError("Go-down Owner Name can not be empty!")
            
    @api.constrains('godown_owner_address')
    def _check_godownowner_address_length(self):
        limit = 200
        record = self.godown_owner_address
        field_name = "Go-down Owner Address"    
        validator._check_length(self, record, limit, field_name)
