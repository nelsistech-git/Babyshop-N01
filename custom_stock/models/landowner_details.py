from odoo import api, exceptions, fields, models
from odoo.addons.helper import validator
#from odoo.addons.base_phone.fields import Phone, Fax
from odoo.addons.phone_validation.tools import phone_validation

class LandOwnerDetails(models.Model):
    _name = 'landowner.details'
    _description = "Landowner Details"
    
    name = fields.Char(string="Name", size=100)
#    phone = fields.Char(string="Contact Number",size=15)
    #phone = Phone(country_field='country_id', size=15)
    phone = fields.Char('Phone', tracking=50)
    
    land_owner_address = fields.Text(string="Address", help="Address can be maximum 200 characters")
    email = fields.Char(string="Email", size=50)
    country_id = fields.Many2one("res.country", string="Country")
    store_id = fields.Many2one("stock.location", string="Branch", ondelete="cascade")
    
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
            
    @api.onchange("name")
    def _onchange_name(self):
        if self.name:        
            self.name = str(self.name).strip()
            
    @api.constrains('name')
    def _check_name_validation(self):
            if self.name == False:
                raise exceptions.ValidationError("Land Owner Name can not be empty!")
            
    @api.constrains('land_owner_address')
    def _check_landowner_address_length(self):
        limit = 200
        record = self.land_owner_address 
        field_name = "Land Owner Address"    
        validator._check_length(self, record, limit, field_name)
            

    
