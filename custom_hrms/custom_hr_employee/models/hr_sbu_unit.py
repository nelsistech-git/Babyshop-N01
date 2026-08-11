# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons.helper import validator


class HrSbuUnit(models.Model):
    _name = 'hr.sbu.unit'
    _description = 'Business Unit'

    name = fields.Char('SBU Name', index=True, required=True, copy=False)
    code = fields.Char('Code', default='New', index=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    sbu_tower_id = fields.Many2one('hr.employee', string="SBU Tower", help='Select Corresponding Employee')
    sbu_head_id = fields.Many2one('hr.employee', string="SBU Head", help='Select Corresponding Employee')
    hr_unit_manager_id = fields.Many2one('hr.employee', string='HR Unit Manager')
    marketing_unit_manager_id = fields.Many2one('hr.employee', string='Marketing Unit Manager')
    active = fields.Boolean(default=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Name "%s"' % self.name
        envobj = self.env['hr.sbu.unit']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('code')
    def _check_unique_constraint_name(self):
        msg = 'Code "%s"' % self.code
        envobj = self.env['hr.sbu.unit']
        conditionlist = [('code', '=', self.code)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if 'code' not in val or val['code'] == _('New'):
                sequence = self.env['ir.sequence'].next_by_code('hr.sbu.unit.code') or _('New')
                val['code'] = sequence
        res = super(HrSbuUnit, self).create(vals)
        return res
