# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTnaMilestone(models.Model):
    """Milestone Management (SRS section 11) — garment.tna.milestone."""
    _name = 'garment.tna.milestone'
    _description = 'Garment TNA Milestone'
    _inherit = ['mail.thread']
    _order = 'due_date'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    # FIXED: Changed tna_id to parent.id in domain
    activity_id = fields.Many2one('garment.tna.activity', string='Source Activity',
                                   domain="[('tna_id', '=', parent.id)]")
    milestone_name = fields.Char(string='Milestone Name', required=True, tracking=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person')
    dependency = fields.Char(string='Dependency')
    status = fields.Selection([
        ('pending', 'Pending'), ('achieved', 'Achieved'), ('missed', 'Missed'),
    ], string='Status', default='pending', tracking=True)
    risk_level = fields.Selection([
        ('normal', 'Normal'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='normal', tracking=True)

    def action_mark_achieved(self):
        self.write({'status': 'achieved'})