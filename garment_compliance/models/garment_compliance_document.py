# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Compliance Document Management (SRS1 sec. 15, SRS2 sec. 8) —
garment.compliance.document. Generic compliance documents (policies, SOPs,
training records, audit reports, safety documents) with version control
and digital approval. Certificates/licenses with a hard expiry date are
tracked separately on garment.compliance.certificate, which is the more
specific, expiry-driven register.
"""
from odoo import fields, models


class GarmentComplianceDocument(models.Model):
    _name = 'garment.compliance.document'
    _description = 'Garment Compliance Document'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True, tracking=True)
    document_type = fields.Selection([
        ('policy', 'Policy'),
        ('sop', 'SOP Document'),
        ('training_record', 'Training Record'),
        ('audit_report', 'Audit Report'),
        ('safety_document', 'Safety Document'),
        ('other', 'Other'),
    ], string='Document Type', required=True, default='policy')
    standard_id = fields.Many2one('garment.compliance.standard', string='Related Standard')
    department_id = fields.Many2one('garment.hr.department', string='Department')
    version = fields.Char(string='Version', default='1.0')
    attachment = fields.Binary(string='File', attachment=True)
    attachment_filename = fields.Char(string='Filename')
    upload_date = fields.Date(string='Upload Date', default=fields.Date.context_today)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    approval_date = fields.Date(string='Approval Date')
    notes = fields.Text(string='Notes')

    def action_approve(self):
        self.write({
            'approval_status': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Date.context_today(self),
        })

    def action_reject(self):
        self.write({'approval_status': 'rejected'})
