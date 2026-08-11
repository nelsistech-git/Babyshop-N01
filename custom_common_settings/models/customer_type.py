import logging

from odoo import fields, models, api
from odoo.addons.helper import validator

_logger = logging.getLogger(__name__)


class CustomerType(models.Model):
    _name = 'customer.type'
    _description = 'Customer Type'
    _rec_name = 'type'

    type = fields.Selection([
        ('r', 'Regular'),
        ('c', 'Corporates & Institutions'),
        ('u', 'End consumers or users'),
        ('i', 'Inter company'),
        ('s', 'Staffs of the company'),
        ('ss', 'Super stores'),
        ('oe', 'Own e-commerce'),
        ('ex', '3rd party')
    ], string='Customer Type')
    name = fields.Char(string='Name')
    description = fields.Text(string='Description')

    def name_get(self):
        result = []
        for rec in self:
            if rec.type:
                type_name = dict(self._fields['type'].selection).get(rec.type)
                if type_name:
                    name = type_name + "(" + rec.type + ")"
                    result.append((rec.id, name))
            elif rec.name:
                result.append((rec.id, rec.name))
        if result:
            return result

    @api.constrains('type')
    def _check_unique_type(self):
        for rec in self:
            type_name = dict(self._fields['type'].selection).get(rec.type)
            msg = 'Type "%s"' % type_name
            envobj = self.env['customer.type']
            conditionlist = [('type', '=', rec.type)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)


class CustomerCategory(models.Model):
    _name = 'customer.category'
    _description = 'Customer Category'

    sequence = fields.Integer(index=True, help="Give the sequence no.", default=1)
    name = fields.Char(string='Customer Category')
    note = fields.Text(string='Note')
