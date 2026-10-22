# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentProductionApproval(models.Model):
    """Production Approval Workflow step log: Production Plan -> Manager
    Approval -> Line Assignment -> Production Start -> Completion Approval.
    See Shop Floor SRS s.43 (Production Approval Workflow)."""
    _name = 'garment.production.approval'
    _description = 'Garment Production Approval Step'
    _order = 'sequence'

    plan_id = fields.Many2one('garment.production.plan', string='Production Plan', ondelete='cascade')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order', ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_step = fields.Selection([
        ('plan_approval', 'Production Plan Approval'), ('line_assignment', 'Line Assignment'),
        ('production_start', 'Production Start'), ('completion_approval', 'Completion Approval'),
    ], string='Approval Step', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    comments = fields.Text(string='Comments')
    signed_date = fields.Datetime(string='Signed Date')

    def action_approve(self):
        self.write({'status': 'approved', 'signed_date': fields.Datetime.now(), 'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'signed_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
