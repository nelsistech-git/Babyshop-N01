# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class GarmentDocumentRetentionPolicy(models.Model):
    """Document retention / archival rule (SRS section 50-51 — "Document
    Retention Policy" / "Document Archive Management"). Document
    Controllers define, per Category / Department / Document Type, how long
    a document must be kept and what should happen once it lapses. Kept as
    configuration data (not hard-coded) so new rules — a new certificate
    type, a new government requirement — never need a developer.

    Example (SRS section 50):
        Employee Document -> Keep 7 Years
        Financial Document -> Keep 10 Years
        Audit Document -> Keep Permanent
    """
    _name = 'garment.document.retention.policy'
    _description = 'Document Retention Policy'
    _order = 'sequence, name'

    name = fields.Char(string='Policy Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    category_id = fields.Many2one('garment.document.category', string='Category',
                                   help='Leave empty to apply to every category.')
    department = fields.Selection([
        ('commercial', 'Commercial'),
        ('production', 'Production'),
        ('hr', 'HR'),
        ('compliance', 'Compliance'),
        ('finance', 'Finance'),
        ('quality', 'Quality'),
        ('logistics', 'Logistics'),
        ('general', 'General / Other'),
    ], string='Department', help='Leave empty to apply to every department.')
    document_type = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('certificate', 'Certificate'),
        ('report', 'Report'),
        ('policy', 'Policy'),
        ('drawing', 'Drawing'),
        ('technical', 'Technical Document'),
        ('other', 'Other'),
    ], string='Document Type', help='Leave empty to apply to every document type.')

    is_permanent = fields.Boolean(string='Keep Permanently',
                                   help='Audit-type documents are typically retained forever '
                                        '(SRS section 50 example).')
    retention_years = fields.Integer(string='Retention Period (Years)', default=7,
                                      help='Ignored when "Keep Permanently" is checked.')
    notice_days = fields.Integer(string='Expiry Reminder (Days Before)', default=30)
    action_on_expiry = fields.Selection([
        ('notify', 'Notify Only'),
        ('archive', 'Auto-Archive'),
        ('lock', 'Lock (Read-Only)'),
    ], string='Action On Expiry', default='notify', required=True,
        help='What garment.document._cron_check_expiring_documents() should do once a '
             'document governed by this policy reaches its expiry date.')

    document_ids = fields.One2many('garment.document', 'retention_policy_id', string='Documents')
    document_count = fields.Integer(string='Documents', compute='_compute_document_count')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'A retention policy with this code already exists!'),
    ]

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def _matching_domain(self):
        self.ensure_one()
        domain = []
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        if self.department:
            domain.append(('department', '=', self.department))
        if self.document_type:
            domain.append(('document_type', '=', self.document_type))
        return domain

    def compute_expiry_date(self, issue_date):
        """Return the expiry date this policy implies for a document issued
        on ``issue_date``, or False if the policy keeps documents
        permanently or no issue date is given."""
        self.ensure_one()
        if self.is_permanent or not issue_date:
            return False
        return issue_date + relativedelta(years=self.retention_years or 0)

    def action_apply_to_matching_documents(self):
        """Bulk-assign this policy (and, where possible, an expiry date) to
        every currently-matching document that has no retention policy set
        yet — SRS section 51 "Archive Rules"."""
        Document = self.env['garment.document']
        for policy in self:
            docs = Document.search(policy._matching_domain() + [('retention_policy_id', '=', False)])
            for doc in docs:
                vals = {'retention_policy_id': policy.id}
                if not doc.expiry_date and doc.issue_date:
                    computed = policy.compute_expiry_date(doc.issue_date)
                    if computed:
                        vals['expiry_date'] = computed
                doc.write(vals)

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'garment.document',
            'view_mode': 'tree,form',
            'domain': [('retention_policy_id', '=', self.id)],
            'context': {'default_retention_policy_id': self.id},
        }
