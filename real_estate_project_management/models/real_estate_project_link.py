# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateLandProjectLink(models.Model):
    """Phase 2: attach a Land record to the Project developed on it.

    This extends the Phase 1 real.estate.land model via _inherit rather
    than modifying land.py directly, per the specification's rule to
    never rebuild/duplicate existing definitions - only extend them.
    """
    _inherit = 'real.estate.land'

    project_id = fields.Many2one('real.estate.project', string='Project',
                                  tracking=True, ondelete='set null')


class RealEstateLandAgreementProjectLink(models.Model):
    """Phase 2: attach a Land Agreement to its Project."""
    _inherit = 'real.estate.land.agreement'

    project_id = fields.Many2one('real.estate.project', string='Project',
                                  tracking=True, ondelete='set null')
