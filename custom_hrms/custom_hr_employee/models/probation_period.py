# coding=utf-8
from odoo import fields, models, api
from odoo.addons.helper import validator


class ProbationPeriod(models.Model):
    """ To create probation period length """
    _name = 'hr.probation.period'
    _description = 'Probation Period'
    _order = 'sequence'

    length = fields.Integer(string='Value', required=True, default=0)

    unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], required=True, default="months")

    name = fields.Char(string='name', required=False, compute='_get_concatenate_values', store=True,
                       readonly=True)
    sequence = fields.Integer(string='Sequence', default=0)
    active = fields.Boolean(string='Active', default=True)

    @api.onchange('length')
    def _remove_space_length(self):
        for r in self:
            if r.length < 0:
                r.length = 0

    @api.depends('length', 'unit')
    def _get_concatenate_values(self):
        for record in self:
            if record.unit:
                record.name = "%d %s" % (record.length, record.unit)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = "Probation Period"
        envobj = self.env['hr.probation.period']

        conditionlist1 = [('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist1, msg)
