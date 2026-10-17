# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class NelsisLcSetting(models.Model):
    """Per-company configurable LC rules (reminders and closure/clearance controls).

    Nothing here is a statutory value.  Every control is a company policy switch
    and must be confirmed by the company's customs/compliance professional.
    """
    _name = 'nelsis.lc.setting'
    _description = 'LC Management Settings'
    _rec_name = 'company_id'

    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company)
    expiry_reminder_days = fields.Integer('LC Expiry Reminder (days before)', default=30)
    shipment_reminder_days = fields.Integer('Shipment Deadline Reminder (days before)', default=15)
    document_reminder_days = fields.Integer('Pending Document Reminder (days before due)', default=7)
    block_close_pending_documents = fields.Boolean('Block closure while required documents are pending', default=True)
    block_close_open_shipments = fields.Boolean('Block closure while shipments are not received/cancelled', default=True)
    block_close_pending_boe = fields.Boolean('Block closure while Bills of Entry are not cleared/cancelled', default=True)
    require_boe_for_clearance = fields.Boolean('Require a cleared Bill of Entry before a shipment is marked Customs Cleared', default=True)
    require_receipt_for_received = fields.Boolean('Require a done warehouse receipt before a shipment is marked Received', default=True)
    enforce_maker_checker = fields.Boolean('Approver must differ from LC creator', default=False)
    note = fields.Text('Policy Note')

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 'Only one LC setting record is allowed per company.'),
    ]

    @api.constrains('expiry_reminder_days', 'shipment_reminder_days', 'document_reminder_days')
    def _check_days(self):
        for rec in self:
            if min(rec.expiry_reminder_days, rec.shipment_reminder_days, rec.document_reminder_days) < 0:
                raise ValidationError(_('Reminder intervals cannot be negative.'))

    @api.model
    def get_setting(self, company=None):
        company = company or self.env.company
        rec = self.sudo().search([('company_id', '=', company.id)], limit=1)
        if not rec:
            rec = self.sudo().create({'company_id': company.id})
        return rec
