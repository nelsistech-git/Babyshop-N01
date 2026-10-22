# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentPurchaseApproval(models.Model):
    """Purchase Approval Workflow (SRS sections 9, 19, 42) —
    garment.purchase.approval."""
    _name = 'garment.purchase.approval'
    _description = 'Garment Purchase Approval'
    _order = 'sequence'

    order_id = fields.Many2one('garment.purchase.order', string='Purchase Order', ondelete='cascade')
    requisition_id = fields.Many2one('garment.purchase.requisition', string='Purchase Requisition',
                                      ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_level = fields.Selection([
        ('department_manager', 'Department Manager'), ('purchase_manager', 'Purchase Manager'),
        ('finance', 'Finance'), ('director', 'Director'), ('managing_director', 'Managing Director'),
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
            # Only approve the PO once every approval record raised for it
            # (the full chain implied by its Approval Matrix tier — e.g. both
            # Finance and Director for the 5-20 Lakh BDT tier, SRS section 42)
            # has been approved.
            if rec.order_id and all(a.status == 'approved' for a in rec.order_id.approval_ids):
                rec.order_id.action_approve()

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
