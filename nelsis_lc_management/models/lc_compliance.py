# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models


class NelsisLcComplianceRef(models.Model):
    """Compliance mapping register.

    Holds legal references that the company's customs professional has
    identified.  The module ships with NO pre-filled legal rules: every entry
    is entered by the company and starts as 'Unverified'.
    """
    _name = 'nelsis.lc.compliance.ref'
    _description = 'LC Compliance Reference'
    _order = 'name'

    name = fields.Char('Rule / SRO Reference', required=True)
    source_url = fields.Char('Official Source URL')
    publication_date = fields.Date()
    effective_date = fields.Date()
    amendment_status = fields.Char('Amendment Status')
    process_affected = fields.Text('Business Process Affected')
    required_documents = fields.Text('Required Supporting Documents')
    user_controls = fields.Text('Applicable Controls / Reports')
    verification_status = fields.Selection([
        ('unverified', 'Unverified'),
        ('in_review', 'In Review'),
        ('verified', 'Verified'),
    ], default='unverified', required=True)
    reviewer = fields.Char('Reviewed By (customs/compliance professional)')
    reviewed_date = fields.Date()
    note = fields.Text()
    active = fields.Boolean(default=True)
