# -*- coding: utf-8 -*-
"""Technical and implementation teams (SRS 14 / 29)."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TEAM_TYPE_SELECTION = [
    ('technical', 'Technical / Survey'),
    ('implementation', 'Implementation / Installation'),
    ('both', 'Technical & Implementation'),
]


class GcErmTeam(models.Model):
    _name = 'gc.erm.team'
    _description = 'GC ERM Technical / Implementation Team'
    _order = 'sequence, name'

    name = fields.Char(string='Team Name', required=True, translate=True)
    code = fields.Char(string='Code', copy=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, index=True)
    team_type = fields.Selection(
        TEAM_TYPE_SELECTION, string='Team Type', required=True,
        default='technical', index=True)
    leader_id = fields.Many2one(
        'res.users', string='Team Leader', domain="[('share', '=', False)]")
    member_ids = fields.Many2many(
        'res.users', 'gc_erm_team_user_rel', 'team_id', 'user_id',
        string='Members', domain="[('share', '=', False)]")
    member_count = fields.Integer(
        string='Number of Members', compute='_compute_member_count')
    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('gc_team_code_uniq', 'unique(code, company_id)',
         'The team code must be unique per company.'),
    ]

    @api.depends('member_ids')
    def _compute_member_count(self):
        for team in self:
            team.member_count = len(team.member_ids)

    @api.constrains('leader_id', 'member_ids')
    def _check_leader_is_member(self):
        for team in self:
            if team.leader_id and team.member_ids and \
                    team.leader_id not in team.member_ids:
                # Not an error, just keep the data consistent.
                team.member_ids = [(4, team.leader_id.id)]

    @api.constrains('team_type', 'member_ids')
    def _check_members(self):
        for team in self:
            if team.active and not (team.member_ids or team.leader_id):
                raise ValidationError(_(
                    'Team "%s" must have at least a leader or one member.',
                    team.name))

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for team in self:
            team.display_name = '[%s] %s' % (team.code, team.name) \
                if team.code else team.name
