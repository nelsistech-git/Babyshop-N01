# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateHandoverChecklistLine(models.Model):
    _name = 'real.estate.handover.checklist.line'
    _description = 'Real Estate Handover Checklist Item'
    _order = 'id'

    handover_id = fields.Many2one('real.estate.handover', string='Handover',
                                   required=True, ondelete='cascade')
    item_name = fields.Char(string='Item', required=True)
    is_checked = fields.Boolean(string='Delivered / Confirmed')
    remarks = fields.Char(string='Remarks')
