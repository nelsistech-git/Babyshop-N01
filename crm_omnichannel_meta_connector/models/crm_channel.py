# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmChannel(models.Model):
    _inherit = 'crm.channel'

    # --- Facebook Messenger ---------------------------------------------------
    meta_page_id = fields.Char(
        string='Facebook Page ID',
        help='The numeric Page ID from Meta Business Suite. Used to route '
             'inbound Messenger webhooks to this channel record.')
    page_access_token = fields.Char(
        string='Page Access Token',
        groups='crm_omnichannel_hub.group_omni_manager',
        help='Long-lived Page Access Token generated in the Meta App Dashboard. '
             'Restricted to Managers: this grants full send/manage access to the Page.')

    # --- Instagram ---------------------------------------------------------
    meta_ig_account_id = fields.Char(
        string='Instagram Business Account ID',
        help='The IG Business Account ID linked to your Facebook Page.')

    # --- WhatsApp ---------------------------------------------------------
    whatsapp_phone_number_id = fields.Char(
        string='WhatsApp Phone Number ID',
        help='The Phone Number ID (not the phone number itself) from the '
             'WhatsApp Business Platform / Cloud API.')
    whatsapp_business_account_id = fields.Char(string='WhatsApp Business Account ID')
    whatsapp_access_token = fields.Char(
        string='WhatsApp Access Token',
        groups='crm_omnichannel_hub.group_omni_manager')

    # --- Shared webhook security ---------------------------------------------------
    app_secret = fields.Char(
        string='Meta App Secret',
        groups='crm_omnichannel_hub.group_omni_manager',
        help='Used to verify the X-Hub-Signature-256 header on every inbound '
             'webhook call. Required - webhooks are rejected if this is empty.')
    verify_token = fields.Char(
        string='Webhook Verify Token',
        groups='crm_omnichannel_hub.group_omni_manager',
        help='Arbitrary string of your choosing. Enter the same value here '
             'and in the Meta App Dashboard webhook configuration screen.')
    webhook_url = fields.Char(string='Webhook URL', compute='_compute_webhook_url',
                               help='Configure this exact URL in the Meta App Dashboard.')

    @api.depends('code')
    def _compute_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.webhook_url = f'{base_url}/omni/webhook/meta'
