# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentSampleApproval(models.Model):
    """Sample Approval Workflow (SRS section 16 + 24) — garment.sample.approval.
    Internal chain: QC → Merchandising Review → Manager Approval → Buyer
    Submission. Buyer chain: Submitted → Buyer Review → Approved/Comments/Rejected."""
    _name = 'garment.sample.approval'
    _description = 'Garment Sample Approval'
    _order = 'sequence'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_stage = fields.Selection([
        ('sample_qc', 'Sample QC'), ('merchandising_review', 'Merchandising Review'),
        ('manager_approval', 'Manager Approval'), ('buyer_submission', 'Buyer Submission'),
        ('buyer_review', 'Buyer Review'), ('buyer_approved', 'Buyer Approved'),
        ('buyer_commented', 'Buyer Commented'), ('buyer_rejected', 'Buyer Rejected'),
    ], string='Approval Stage', required=True)
    # Approval Types (SRS section 24) — the category of approval being recorded, independent of
    # which internal/buyer workflow stage (approval_stage, above) it happened at.
    approval_type = fields.Selection([
        ('design', 'Design Approval'), ('fit', 'Fit Approval'), ('color', 'Color Approval'),
        ('measurement', 'Measurement Approval'), ('pp', 'PP Approval'), ('final', 'Final Approval'),
    ], string='Approval Type')
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    approval_date = fields.Datetime(string='Approval Date')
    comments = fields.Text(string='Comments')
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')

    def action_approve(self):
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
        for rec in self:
            rec.sample_id.message_post(
                body=_('Approval "%s" (%s) approved by %s.') % (
                    dict(rec._fields['approval_stage'].selection).get(rec.approval_stage, rec.approval_stage),
                    dict(rec._fields['approval_type'].selection).get(rec.approval_type, '-') if rec.approval_type else '-',
                    rec.approver_id.name))

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
        for rec in self:
            rec.sample_id.message_post(
                body=_('Approval "%s" rejected by %s.') % (
                    dict(rec._fields['approval_stage'].selection).get(rec.approval_stage, rec.approval_stage),
                    rec.approver_id.name))
