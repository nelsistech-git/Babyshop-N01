# -*- coding: utf-8 -*-
from odoo import models, fields


class BsPfCommittee(models.Model):
    _name = 'pf.committee'
    _description = 'PF Committee'

    type = fields.Selection([('pf', 'PF'), ('wppf', 'WPPF')], default='pf', string='Type', required=True)

    name = fields.Char(string='Name', required=True)
    date_committee = fields.Date(string='Committee Start Date', required=True, default=fields.Date.today())
    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Board", index=True, required=True)
    committee_line = fields.One2many(comodel_name='pf.committee.line', inverse_name='pf_committee_id',
                                     string='Committee Line')


class BsPfCommitteeLine(models.Model):
    _name = 'pf.committee.line'
    _description = 'PF Committee Line'

    pf_committee_id = fields.Many2one(comodel_name='pf.committee', string='Committee ID', required=True,
                                      ondelete='restrict', index=True)

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    job_id = fields.Many2one(comodel_name='hr.job', related='employee_id.job_id', readonly=True)
    pf_job_id = fields.Many2one(comodel_name='pf.committee.job', string='PF Designation', required=True)
    is_active = fields.Boolean(string='Active', required=True, default=True)
    active_from = fields.Date(string='From', required=True, default=fields.Date.today())
    active_to = fields.Date(string='To')


class BsPFCommitteeJob(models.Model):
    _name = 'pf.committee.job'
    _description = 'PF Committee Job'

    name = fields.Char(string='Job Name', required=True)
