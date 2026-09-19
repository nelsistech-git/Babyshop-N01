# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwSeason(models.Model):
    _name = 'fw.season'
    _description = 'Footwear Season Master'
    _order = 'date_start desc, name'

    name = fields.Char(string='Season Name', required=True, tracking=True,
                        help="E.g. Spring/Summer 2027, Fall/Winter 2026")
    code = fields.Char(string='Season Code', required=True, tracking=True)
    date_start = fields.Date(string='Start Date', tracking=True)
    date_end = fields.Date(string='End Date', tracking=True)
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('planning', 'Planning'),
        ('development', 'Development'),
        ('production', 'In Production'),
        ('closed', 'Closed'),
    ], string='Status', default='planning', tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Season Code must be unique per company!'),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(
                    "Season Start Date cannot be after the End Date for '%s'." % rec.name)

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
