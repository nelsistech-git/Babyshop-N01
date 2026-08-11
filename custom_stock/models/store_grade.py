from odoo import api, exceptions, fields, models,_
from odoo.addons.helper import validator

class StoreGrade(models.Model):
    _name = "store.grade"
    _description = "Store Grade"
    
    name = fields.Char(string="Name", size=100, required=True, help="Name can be maximum 100 characters")
    is_range = fields.Boolean(string="Is Range", default=True)
    from_value = fields.Integer(string="From Number", size=8)
    to_value = fields.Integer(string="To Number", size=8)
    active = fields.Boolean(string="Active", default=True)
    description=fields.Text(string="Description", help="Description can be maximum 300 characters")
    
    @api.onchange("name")
    def _onchange_name(self):
        if self.name:        
            self.name = str(self.name).strip()
        
    @api.constrains('name')
    def _check_unique_constraint(self):
        
        msg = "Grade Name"
        
        envObj=self.env['store.grade']
        conditionList=[('name', '=ilike', self.name),'|',('active', '=', True),('active', '=', False)]
        
        validator.check_duplicate_value(self,envObj,conditionList,msg)
    
    @api.onchange("is_range")
    def _onchange_is_range(self):        
        if self.is_range==False:
            self.to_value=0
            
    @api.onchange("from_value")
    def _onchange_from_value(self):
        length=8
        if len(str(self.from_value)) > length:
            field_name="From Number"
            from_value = self.from_value
            self.from_value = validator._check_integer(self,from_value,length)
            return   {
                    'warning': {
                        'title': _('Warning'),
                    'message': _('%s can not be more than %d digits!'%(field_name,length)),
                        }}
    
    @api.onchange("to_value")
    def _onchange_to_value(self):
        length=8
        if len(str(self.to_value)) > length:
            field_name="From Number"
            to_value = self.to_value
            self.to_value = validator._check_integer(self,to_value,length)
            return   {
                    'warning': {
                        'title': _('Warning'),
                    'message': _('%s can not be more than %d digits!'%(field_name,length)),
                        }}
            
    @api.constrains('is_range','from_value','to_value')
    def _check_from_value(self):
        if self.is_range:
            if self.from_value<0:
                raise exceptions.ValidationError(_("'From Number' can not be negative!"))
            elif self.to_value<0:
                raise exceptions.ValidationError(_("'To Number' can not be negative!"))
            elif self.from_value>=self.to_value:
                raise exceptions.ValidationError(_("'To Number' can not be equal or less than 'From Number'!"))
        else:            
            if self.from_value<=0:
                raise exceptions.ValidationError(_("'From Number' must be positive!"))
    
    @api.constrains('description')
    def _check_grade_description_length(self):
        limit=300
        record = self.description
        field_name = "Description"    
        validator._check_length(self,record,limit,field_name)
    
    
    def name_get(self):
        result = []
        for record in self:
            name =record.name + ' ' + '[' + str(record.from_value) + '-'+ str(record.to_value) + ']' 
            result.append((record.id, name))
        return result
    
    
    