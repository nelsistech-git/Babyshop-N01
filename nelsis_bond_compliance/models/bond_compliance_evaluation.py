# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import _, fields, models
from odoo.exceptions import UserError


class BondComplianceEvaluation(models.Model):
    """Immutable log of rule evaluations.

    Every logged evaluation keeps a reference to the exact rule version used, so
    later rule changes, supersession or expiry never alter historical results.
    """
    _name = 'bond.compliance.evaluation'
    _description = 'Bond Compliance Evaluation Log'
    _order = 'evaluated_at desc, id desc'

    name = fields.Char(readonly=True)
    rule_id = fields.Many2one(
        'bond.compliance.rule', string='Rule Version', readonly=True,
        ondelete='restrict', index=True)
    rule_code = fields.Char(readonly=True, index=True)
    rule_version = fields.Integer(readonly=True)
    official_reference = fields.Char(readonly=True)
    res_model = fields.Char(string='Document Model', readonly=True)
    res_id = fields.Integer(string='Document ID', readonly=True)
    reference = fields.Char(string='Transaction Reference', readonly=True, index=True)
    evaluated_on = fields.Date(string='Evaluation Date', readonly=True, index=True)
    evaluated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    evaluated_by = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True)
    status = fields.Selection(
        [('passed', 'Passed'), ('failed', 'Failed'), ('no_rule', 'No Applicable Rule'),
         ('ambiguous', 'Ambiguous Rule')], readonly=True, index=True)
    passed = fields.Boolean(readonly=True)
    covered_by_exception = fields.Boolean(readonly=True)
    result_json = fields.Text(string='Result Snapshot', readonly=True)

    def write(self, vals):
        raise UserError(_('Evaluation log entries are immutable.'))

    def unlink(self):
        raise UserError(_('Evaluation log entries cannot be deleted.'))
