# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstateLandOwnership(models.Model):
    """Relational line: links a Land to a Land Owner with an ownership %.

    A land can have multiple owners. The sum of ownership_percentage for
    all lines of a given land must equal 100 before the land can be
    verified/activated (enforced on real.estate.land, not here, since a
    land is expected to be built up line by line before reaching 100%).
    """
    _name = 'real.estate.land.ownership'
    _description = 'Land Ownership Share'
    _rec_name = 'land_id'
    _order = 'id'

    land_id = fields.Many2one(
        'real.estate.land', string='Land', required=True, ondelete='cascade')
    owner_id = fields.Many2one(
        'real.estate.land.owner', string='Land Owner', required=True,
        ondelete='restrict')
    ownership_percentage = fields.Float(
        string='Ownership %', required=True, digits=(5, 2),
        help='Percentage of the land owned by this owner. Total across '
             'all owners of a land must equal 100%.')
    company_id = fields.Many2one(
        related='land_id.company_id', string='Company', store=True, readonly=True)

    _sql_constraints = [
        ('land_owner_uniq', 'unique(land_id, owner_id)',
         'This owner is already linked to this land. Edit the existing line instead.'),
        ('percentage_range', 'CHECK(ownership_percentage > 0 AND ownership_percentage <= 100)',
         'Ownership percentage must be greater than 0 and not exceed 100.'),
    ]

    @api.constrains('ownership_percentage')
    def _check_percentage_positive(self):
        for rec in self:
            if rec.ownership_percentage <= 0 or rec.ownership_percentage > 100:
                raise ValidationError(
                    'Ownership percentage must be between 0 and 100 for %s.'
                    % rec.owner_id.display_name)
