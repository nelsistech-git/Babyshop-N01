# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentCRMTag(models.Model):
    """Lightweight Buyer CRM tag master.

    The module previously pointed ``garment.opportunity.tag_ids`` at the
    Odoo ``crm.tag`` model, which only exists when the standard ``crm`` app
    is installed. Buyer CRM does not (and should not) depend on ``crm``, so
    that field silently broke on any install that only has this suite's
    modules. This local tag model removes that hidden dependency while
    keeping the same tagging feature described in the SRS (Search & Filter
    Features, section 31: "Tags").
    """
    _name = 'garment.crm.tag'
    _description = 'Garment Buyer CRM Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A tag with this name already exists.'),
    ]
