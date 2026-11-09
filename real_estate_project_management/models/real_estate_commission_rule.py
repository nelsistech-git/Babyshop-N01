# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RealEstateCommissionRule(models.Model):
    """Company-defined commission for each of the 2 layers.

    Level 1 = the person who made the sale (agent, or a customer who sold
              the property to a new buyer).
    Level 2 = the person who had originally referred that Level-1 person.

    Each level can be a % of the sale's net price or a fixed amount. A rule
    with a Project set overrides the global (no-project) rule for that
    project only.
    """
    _name = 'real.estate.commission.rule'
    _description = 'Real Estate Commission Rule'
    _order = 'level, project_id, id'

    name = fields.Char(compute='_compute_name', store=True)
    level = fields.Selection([
        ('1', 'Level 1 - Direct Seller (agent / referrer of this sale)'),
        ('2', 'Level 2 - Upline (who referred the Level 1 person)'),
    ], string='Commission Layer', required=True, default='1')
    calc_type = fields.Selection([
        ('percentage', 'Percentage of Net Price'),
        ('fixed', 'Fixed Amount'),
    ], string='Calculation', required=True, default='percentage')
    value = fields.Float(string='Percent / Amount', required=True, digits=(16, 2))
    project_id = fields.Many2one(
        'real.estate.project', string='Project',
        help='Leave empty to apply to ALL projects. A project-specific rule wins '
             'over the global rule.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    notes = fields.Text(string='Notes')

    @api.depends('level', 'calc_type', 'value', 'project_id')
    def _compute_name(self):
        for rec in self:
            amount = ('%.2f%%' % rec.value) if rec.calc_type == 'percentage' else ('%.2f fixed' % rec.value)
            scope = rec.project_id.project_name or _('All Projects')
            rec.name = _('Level %(level)s - %(amount)s (%(scope)s)',
                         level=rec.level, amount=amount, scope=scope)

    @api.constrains('value', 'calc_type')
    def _check_value(self):
        for rec in self:
            if rec.value < 0:
                raise ValidationError(_('Commission value cannot be negative.'))
            if rec.calc_type == 'percentage' and rec.value > 100:
                raise ValidationError(_('A percentage commission cannot exceed 100%.'))

    @api.constrains('level', 'project_id', 'company_id', 'active')
    def _check_single_active_rule(self):
        for rec in self.filtered('active'):
            dup = self.search_count([
                ('id', '!=', rec.id), ('active', '=', True), ('level', '=', rec.level),
                ('project_id', '=', rec.project_id.id), ('company_id', '=', rec.company_id.id)])
            if dup:
                raise ValidationError(_(
                    'Only one active rule is allowed per layer / project / company. '
                    'Archive the existing Level %s rule first.') % rec.level)

    @api.model
    def _get_rule(self, level, project=None, company=None):
        """Project-specific rule first, then the global rule, else empty."""
        company = company or self.env.company
        rules = self.sudo().search([
            ('level', '=', str(level)), ('active', '=', True),
            ('company_id', 'in', [False, company.id])])
        if project:
            specific = rules.filtered(lambda r: r.project_id == project)
            if specific:
                return specific[:1]
        return rules.filtered(lambda r: not r.project_id)[:1]
