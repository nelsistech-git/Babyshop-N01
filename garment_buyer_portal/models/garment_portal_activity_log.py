# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentPortalActivityLog(models.Model):
    """Buyer Portal Audit Trail (SRS section 46) — garment.portal.activity.log.

    Written by the portal controller (see controllers/portal.py) on every
    login, document view, download, approval decision and comment. Never
    edited from the UI - `log()` is the only intended write path.
    """
    _name = 'garment.portal.activity.log'
    _description = 'Buyer Portal Activity Log'
    _order = 'activity_date desc, id desc'
    _rec_name = 'description'

    partner_id = fields.Many2one('res.partner', string='Buyer User', required=True, index=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', index=True)

    activity_type = fields.Selection([
        ('login', 'Login'),
        ('view_order', 'Viewed Order'),
        ('view_sample', 'Viewed Sample'),
        ('view_shipment', 'Viewed Shipment'),
        ('view_quality', 'Viewed Quality Report'),
        ('view_approval', 'Viewed Approval'),
        ('approval_decision', 'Approval Decision'),
        ('download_document', 'Downloaded Document'),
        ('comment', 'Added Comment'),
        ('account_approved', 'Portal Account Approved'),
        ('other', 'Other'),
    ], string='Activity Type', required=True)

    res_model = fields.Char(string='Related Document Model')
    res_id = fields.Integer(string='Related Document ID')
    description = fields.Char(string='Description', required=True)

    activity_date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @staticmethod
    def _client_meta(http_request):
        """Extract (ip_address, user_agent) from an odoo.http.request, if given."""
        if http_request is None:
            return False, False
        ip_address = getattr(http_request.httprequest, 'remote_addr', False)
        user_agent = http_request.httprequest.user_agent
        return ip_address, (str(user_agent) if user_agent else False)

    def log(self, partner, activity_type, description, res_model=False, res_id=False, http_request=None):
        """Convenience creator used by the portal controllers.

        `partner` may be a `res.partner` recordset; `http_request` is the
        `odoo.http.request` object when available, used to capture the IP
        address / user agent for the audit trail (SRS section 46).
        """
        ip_address, user_agent = self._client_meta(http_request)
        return self.sudo().create({
            'partner_id': partner.id if partner else False,
            'buyer_id': partner.garment_buyer_id.id if partner and partner.garment_buyer_id else False,
            'activity_type': activity_type,
            'description': description,
            'res_model': res_model,
            'res_id': res_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
        })
