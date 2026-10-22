# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentCostingApproval(models.Model):
    """Cost Approval Workflow (SRS section 39) — garment.costing.approval.
    4 levels: Merchandising -> Costing Team -> Finance -> Management."""
    _name = 'garment.costing.approval'
    _description = 'Garment Costing Approval'
    _order = 'sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_level = fields.Selection([
        ('merchandising', 'Level 1: Merchandising Approval'), ('costing_team', 'Level 2: Costing Team Approval'),
        ('finance', 'Level 3: Finance Approval'), ('management', 'Level 4: Management Approval'),
    ], string='Approval Level', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    approval_date = fields.Datetime(string='Approval Date')
    comments = fields.Text(string='Comments')

    def action_approve(self):
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
        for rec in self:
            if rec.approval_level == 'management':
                rec.costing_id.action_lock()

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
