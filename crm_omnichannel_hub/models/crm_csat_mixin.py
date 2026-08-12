# -*- coding: utf-8 -*-
import secrets

from odoo import api, fields, models, _


class CrmCsatMixin(models.AbstractModel):
    _name = 'crm.csat.mixin'
    _description = 'Customer Satisfaction Survey Mixin'

    csat_token = fields.Char(string='CSAT Token', copy=False, index=True)
    customer_rating = fields.Selection([
        ('1', '1 - Very Dissatisfied'),
        ('2', '2 - Dissatisfied'),
        ('3', '3 - Neutral'),
        ('4', '4 - Satisfied'),
        ('5', '5 - Very Satisfied'),
    ], string='Customer Rating', copy=False)
    customer_feedback = fields.Text(string='Customer Feedback', copy=False)
    csat_requested_date = fields.Datetime(string='Survey Sent', copy=False)
    csat_submitted_date = fields.Datetime(string='Survey Submitted', copy=False)

    def _get_csat_token(self):
        self.ensure_one()
        if not self.csat_token:
            self.sudo().write({'csat_token': secrets.token_urlsafe(24)})
        return self.csat_token

    def action_request_csat(self):
        """Generate a survey link and try to deliver it through the most
        recent chat conversation with this customer (works whether the
        record itself is a chat session or a call log)."""
        for rec in self:
            rec._get_csat_token()
            rec.sudo().write({'csat_requested_date': fields.Datetime.now()})
            rec._deliver_csat_link()

    def action_submit_csat(self, rating, feedback=None):
        self.ensure_one()
        self.sudo().write({
            'customer_rating': str(rating),
            'customer_feedback': feedback,
            'csat_submitted_date': fields.Datetime.now(),
        })

    def _deliver_csat_link(self):
        self.ensure_one()
        if not self.partner_id or not self.csat_token:
            return False
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        link = '%s/omni/csat/%s' % (base_url, self.csat_token)
        session = self.env['crm.chat.session'].sudo().search([
            ('partner_id', '=', self.partner_id.id),
        ], order='last_message_date desc', limit=1)
        if not session:
            return False
        self.env['crm.chat.message'].sudo().create({
            'session_id': session.id,
            'direction': 'out',
            'body': _('How did we do? Please rate your experience: %s') % link,
            'message_type': 'text',
        })
        return True
