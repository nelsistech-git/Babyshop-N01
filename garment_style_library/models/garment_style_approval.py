# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleApproval(models.Model):
    """Style Approval Workflow tracking (SRS section 25) — garment.style.approval.
    Approval comments and electronic signatures are stored per approval step."""
    _name = 'garment.style.approval'
    _description = 'Garment Style Approval Step'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_step = fields.Selection([
        ('designer', 'Designer'), ('design_manager', 'Design Manager'),
        ('merchandising_review', 'Merchandising Review'), ('sampling_review', 'Sampling Review'),
        ('qa_verification', 'QA Verification'), ('buyer_approval', 'Buyer Approval'),
    ], string='Approval Step', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    comments = fields.Text(string='Comments')
    signed_date = fields.Datetime(string='Signed Date')
    electronic_signature = fields.Binary(string='Electronic Signature', attachment=True)

    def action_approve(self):
        self.write({'status': 'approved', 'signed_date': fields.Datetime.now(),
                    'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'signed_date': fields.Datetime.now(),
                    'approver_id': self.env.user.id})
