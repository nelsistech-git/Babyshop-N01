# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentTechApproval(models.Model):
    """Approval Workflow + Digital Signature (SRS sections 21-22) —
    garment.tech.approval."""
    _name = 'garment.tech.approval'
    _description = 'Garment Tech Pack Approval'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_stage = fields.Selection([
        ('merchandiser_review', 'Merchandiser Review'), ('technical_manager', 'Technical Manager'),
        ('quality_review', 'Quality Review'), ('production_review', 'Production Review'),
        ('buyer_submission', 'Buyer Submission'), ('buyer_review', 'Buyer Review'), ('buyer_approved', 'Buyer Approved'),
    ], string='Approval Stage', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('modification_requested', 'Modification Requested'),
    ], string='Status', default='pending')
    comments = fields.Text(string='Comments')

    # Digital Signature (SRS section 22)
    signer_name = fields.Char(string='Signer Name')
    designation = fields.Char(string='Designation')
    signed_date = fields.Datetime(string='Signed Date')
    electronic_signature = fields.Binary(string='Electronic Signature', attachment=True)
    signature_ip_address = fields.Char(string='IP Address')
    document_version = fields.Char(string='Document Version')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.approval_stage == 'buyer_submission':
                # Automation Rule (SRS section 31): "Notify buyer after submission".
                rec.techpack_id.message_post(
                    body=_('Tech Pack "%s" (version %s) submitted to the buyer for review.') % (
                        rec.techpack_id.name, rec.techpack_id.version))
        return records

    def action_approve(self):
        for rec in self:
            rec.write({
                'status': 'approved',
                'signed_date': fields.Datetime.now(),
                'approver_id': self.env.user.id,
                'signer_name': self.env.user.name,
                'document_version': rec.techpack_id.version,
            })

    def action_reject(self):
        self.write({'status': 'rejected', 'signed_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
