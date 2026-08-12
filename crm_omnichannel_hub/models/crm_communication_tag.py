# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmCommunicationTag(models.Model):
    _name = 'crm.communication.tag'
    _description = 'Communication Tag'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This tag already exists.'),
    ]
