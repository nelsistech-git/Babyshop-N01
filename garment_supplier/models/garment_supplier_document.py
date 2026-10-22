# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models, _


class GarmentSupplierDocument(models.Model):
    """Supplier Document Management (SRS section 9) —
    garment.supplier.document."""
    _name = 'garment.supplier.document'
    _description = 'Garment Supplier Document'
    _order = 'expiry_date'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('trade_license', 'Trade License'), ('tax_certificate', 'Tax Certificate'), ('bank_details', 'Bank Details'),
        ('compliance_certificate', 'Compliance Certificate'), ('factory_license', 'Factory License'),
        ('environmental_certificate', 'Environmental Certificate'), ('quality_certificate', 'Quality Certificate'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    name = fields.Char(string='Document Name', required=True)
    attachment = fields.Binary(string='File', attachment=True, required=True)
    attachment_filename = fields.Char(string='Filename')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    expiry_status = fields.Selection([
        ('valid', 'Valid'), ('expiring_soon', 'Expiring Soon'), ('expired', 'Expired'),
        ('pending_verification', 'Pending Verification'),
    ], string='Status', compute='_compute_expiry_status', store=True)
    expiry_notified = fields.Boolean(string='Expiry Notification Sent', default=False, copy=False,
                                      help='Set once the Document Expiry notification (SRS section 47) has been '
                                           'sent, so the daily cron does not repeat it every day.')

    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.expiry_status = 'pending_verification'
            elif rec.expiry_date < today:
                rec.expiry_status = 'expired'
            elif rec.expiry_date <= today + timedelta(days=30):
                rec.expiry_status = 'expiring_soon'
            else:
                rec.expiry_status = 'valid'

    @api.model
    def write(self, vals):
        if 'expiry_date' in vals:
            vals.setdefault('expiry_notified', False)
        return super().write(vals)

    @api.model
    def _cron_notify_expiring_documents(self):
        """Document Expiry notification (SRS section 47): 'Certificate
        expires in 15 days'. Posts on the supplier's chatter and raises an
        activity for the Purchase Manager group so it surfaces in their
        activity inbox — Email/SMS/WhatsApp gateways are external
        integrations left for a future connector, per the SRS's own
        multi-channel note."""
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=15)
        docs = self.search([
            ('expiry_date', '!=', False), ('expiry_date', '>=', today), ('expiry_date', '<=', horizon),
            ('expiry_notified', '=', False),
        ])
        managers = self.env.ref('garment_supplier.group_supplier_purchase_manager').users
        for doc in docs:
            days_left = (doc.expiry_date - today).days
            body = _('Document Expiry: "%(doc)s" for supplier %(supplier)s expires in %(days)d day(s) '
                      '(%(date)s).') % {
                'doc': doc.name, 'supplier': doc.supplier_id.name, 'days': days_left, 'date': doc.expiry_date,
            }
            doc.supplier_id.message_post(body=body)
            for user in managers:
                doc.supplier_id.activity_schedule(
                    'mail.mail_activity_data_todo', summary=_('Supplier document expiring soon'),
                    note=body, user_id=user.id)
            doc.expiry_notified = True
