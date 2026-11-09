# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstatePortalLine(models.TransientModel):
    """Generic display row of the customer / agent dashboard.

    The dashboards are built with sudo() from the logged-in user's own
    partner and written into these throw-away transient rows, so customers
    and agents never need (and never get) read access to the real business
    models. One generic row type is re-labelled per list in the views."""
    _name = 'real.estate.portal.line'
    _description = 'Dashboard Row'
    _order = 'sequence, id'
    _transient_max_hours = 12.0

    dashboard_id = fields.Many2one('real.estate.portal.dashboard', required=True, ondelete='cascade')
    line_type = fields.Selection([
        ('property', 'Property'),
        ('schedule', 'Payment Schedule'),
        ('payment', 'Payment Done'),
        ('project', 'Project Expense Summary'),
        ('expense', 'Expense by Head'),
        ('commission', 'Commission'),
        ('customer', 'Customer'),
        ('sale', 'Sale'),
        ('followup', 'Follow-up'),
    ], required=True, index=True)
    sequence = fields.Integer(default=10)

    name = fields.Char()
    ref = fields.Char()
    partner_name = fields.Char()
    project_name = fields.Char()
    unit_name = fields.Char()
    text1 = fields.Char()
    text2 = fields.Char()
    text3 = fields.Char()
    date = fields.Date()
    date2 = fields.Date()
    amount = fields.Monetary()
    amount2 = fields.Monetary()
    amount3 = fields.Monetary()
    amount4 = fields.Monetary()
    percent = fields.Float(digits=(5, 1))
    state_code = fields.Char()
    state_label = fields.Char()
    currency_id = fields.Many2one(related='dashboard_id.currency_id', readonly=True)
