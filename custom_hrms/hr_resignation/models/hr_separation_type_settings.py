# -*- coding: utf-8 -*-
import datetime
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.helper import validator


class HrSeparationTypeSettings(models.Model):
    _name = 'hr.separation.type.settings'
    _description = 'HrSeparationTypeSettings'
    _order = "id desc"

    name =  fields.Char(string='Name')
    # is_fired =  fields.Boolean(string='Is Fired')
    # is_resigned =  fields.Boolean(string='Is Resigned')

    type = fields.Selection([
        ('fired', "Fired"),
        ('resigned', "Resigned"),
    ], string="Type")

    @api.constrains('name')
    def _check_unique_constraint_type_name(self):
        for rec in self:
            name = '"%s"' % rec.name
            envobj = self.env['hr.separation.type.settings']
            conditionlist = [('name', '=', rec.name)]
            validator.check_duplicate_value(rec, envobj, conditionlist, name)
