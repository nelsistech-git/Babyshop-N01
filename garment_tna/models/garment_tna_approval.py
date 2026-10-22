# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTnaApproval(models.Model):
    """Department Review approval workflow (SRS section 7 'Department
    Review' status + section 22) — garment.tna.approval."""
    _name = 'garment.tna.approval'
    _description = 'Garment TNA Approval'
    _order = 'sequence'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    department = fields.Selection([
        ('merchandising', 'Merchandising'), ('product_development', 'Product Development'),
        ('material', 'Material/Purchase'), ('production', 'Production'), ('quality', 'Quality'),
        ('commercial', 'Commercial'),
    ], string='Department', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    approval_date = fields.Datetime(string='Approval Date')
    comments = fields.Text(string='Comments')

    def action_approve(self):
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
