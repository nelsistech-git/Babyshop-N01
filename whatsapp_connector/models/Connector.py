# -*- coding: utf-8 -*-
import hashlib
import hmac
import logging
import json
import sys
import requests
from markupsafe import Markup
from random import randint
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import _tz_get
from ..tools import TIMEOUT, log_request_error, get_image_from_url, phone_format, clean_number
from ..tools import unix_ts_to_naive_utc

from urllib.parse import quote
_logger = logging.getLogger(__name__)


class AcruxChatConnector(models.Model):
    _name = 'acrux.chat.connector'
    _description = 'Connector Definition'
    _order = 'sequence, id'

    # Baileys / Next.js gateway: same HTTP contract as ApiChat.io (`action` header); set host to your app.
    DEFAULT_BAILEYS_GATEWAY_URL = 'http://localhost:3000/api/gateway/v1'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, copy=False, default=_('Unnamed'))
    sequence = fields.Integer('Priority', required=True, default=1)
    message = fields.Html('Message', readonly=True, default='<i>Important information about the status of your '
                                                            'account will be displayed here.<br/>This value is '
                                                            'updated every time you press the "Check Status" '
                                                            'button.</i>')
    connector_type = fields.Selection([('not_set', 'Not set'),
                                       ('apichat.io', 'ApiChat.io'),
                                       ('baileys', 'Baileys (self-hosted WhatsApp)'),
                                       ('gupshup', 'GupShup'),
                                       ('facebook', 'Facebook'),
                                       ('instagram', 'Instagram'),
                                       ('waba_extern', 'Waba Extern')],
                                      string='Connect to', default='apichat.io', required=True,
                                      help='Third-party connector type.')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    team_id = fields.Many2one('crm.team', string='Team', ondelete='set null')
    verify = fields.Boolean('Verify SSL', default=True, help='Set False if SSLError: bad handshake - ' +
                                                             'certificate verify failed.')
    source = fields.Char('Account (Instagram-FaceBook-Whatsapp)', required=True,
                         help='Instagram, FaceBook or Whatsapp phone number.')
    odoo_url = fields.Char('Odoo Url (WebHook)', required=True,
                           default=lambda x: x.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                           help='Url to receive messages. Don\'t use http://localhost')
    endpoint = fields.Char('API Endpoint', required=True, default='https://api.acruxlab.net/prod/v2/odoo',
                           help='API Url. Please don\'t change.')
    token = fields.Char('Token', required=True, copy=False)
    uuid = fields.Char('Account ID', required=True, copy=False)
    time_to_respond = fields.Integer('Time to Respond (Hours)', default=24,
                                     help='Expiry time in hours to respond message without additional fee.\n' +
                                     'Null or 0 indicate no limit.')
    time_to_reasign = fields.Integer('Release unanswered conversation (Minutes)', default=10,
                                     help='Time in which the conversation is released to be taken by another user.')
    time_to_done = fields.Integer('End idle conversation (Days)', default=3,
                                  help='Number of days after which a conversation without movement ends automatically. '
                                       'Prevents your software works slow.')
    border_color = fields.Char(string='Border Color', size=7, compute='_compute_border_color',
                               help="Border color to differentiate conversation connector")
    color = fields.Integer('Color', default=_get_default_color, required=True)
    ca_status = fields.Boolean('Connected', default=False)
    ca_status_txt = fields.Char('Status')
    ca_qr_code = fields.Binary('QR Code')
    reassign_current_conversation = fields.Boolean('Release conversation if Agent\'s inactive',
                                                   default=False,
                                                   help="If the Agent who is attending a conversation is inactive, "
                                                        "when a new message arrives the conversation will go to New "
                                                        "so that another Agent can attend it.")
    tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self.env.context.get('tz'),
                          help='Default value if not defined in the user.')
    desk_notify = fields.Selection([('none', 'None'),
                                    ('mines', 'Only Mines'),
                                    ('all', 'All')], string='Notify', required=True,
                                   default='mines', help='When to send notification outside chatroom?')
    show_icon = fields.Boolean('Show Icon?', default=True)
    webhook_url = fields.Char('Webhook Url', compute='compute_webhook_url', store=False)
    auto_valid_number = fields.Boolean('Validate Numbers', default=False,
                                       help='Check if it exists in WhatsApp and repair.')
    valid_restriction = fields.Boolean('Restriction', default=False)
    validate_conn_id = fields.Many2one('acrux.chat.connector', string='Validate with',
                                       domain="[('connector_type', '=', 'apichat.io'),"
                                              "('validate_conn_id', '=', False),"
                                              "('id', '!=', id)]",
                                       ondelete='set null')
    valid_balance = fields.Integer('Available queries', readonly=True)
    valid_limit = fields.Integer('Query limit', readonly=True)
    valid_date = fields.Date('Until', readonly=True)
    allow_signing = fields.Boolean('Allow Signing', default=False)
    product_caption = fields.Text('Caption',
                                  default='list_price = format_price(product_id.lst_price)\n'
                                          'text = "%s\\n%s / %s" % (product_id.display_name.strip(), '
                                          'list_price, product_id.uom_id.name[:4])\n')
    chatroom_hide_branding = fields.Boolean('Hide Branding', compute='_compute_hide_branding', store=False)
    allowed_lang_ids = fields.Many2many('res.lang', string='Langs', context={'active_test': False},
                                        help='Langs that can be translated in this connector.')
    notify_discuss = fields.Boolean('Notify by Internal Chat', default=True,
                                    help='Send a message through Internal Chat reporting a change in a chat. '
                                         'Example: When another Agent Delegates a chat to you.')

    # Facebook Messenger (direct Graph API — no Acrux relay)
    facebook_graph_api_version = fields.Char(
        string='Graph API Version',
        default='v21.0',
        help='Graph API version segment, e.g. v21.0 (https://graph.facebook.com/{version}/...).',
    )
    facebook_page_access_token = fields.Char(
        string='Page Access Token',
        copy=False,
        help='Long-lived Page access token with pages_messaging. Used to send messages and fetch profile data.',
    )
    facebook_verify_token = fields.Char(
        string='Webhook Verify Token',
        copy=False,
        help='Any secret string you choose; must match the Verify Token in Meta App → Webhooks.',
    )
    facebook_app_secret = fields.Char(
        string='App Secret',
        copy=False,
        help='Optional. If set, Odoo validates X-Hub-Signature-256 on each webhook POST (recommended in production).',
    )
    facebook_page_id = fields.Char(
        string='Facebook Page ID',
        copy=False,
        help='Optional. If set, only webhook events for this Page ID are processed (useful if one app subscribes to multiple pages).',
    )
    facebook_webhook_help = fields.Html(
        string='Facebook Webhook',
        compute='_compute_facebook_webhook_help',
        sanitize=False,
    )
    facebook_messenger_window_hours = fields.Float(
        string='Messenger standard window (hours)',
        default=23.917,
        help='While the PSID\'s latest inbound chat message is within this age, outbound sends '
             'use messaging_type RESPONSE. Slightly below 24h avoids edge-of-window rejects.',
    )
    facebook_outside_window_message_tag = fields.Selection(
        [('none', 'None (always RESPONSE)'),
         ('ACCOUNT_UPDATE', 'ACCOUNT_UPDATE'),
         ('CONFIRMED_EVENT_UPDATE', 'CONFIRMED_EVENT_UPDATE'),
         ('HUMAN_AGENT', 'HUMAN_AGENT'),
         ('POST_PURCHASE_UPDATE', 'POST_PURCHASE_UPDATE'),
         ('PAYMENT_UPDATE', 'PAYMENT_UPDATE'),
         ('SHIPPING_UPDATE', 'SHIPPING_UPDATE'),
         ('RESERVATION_UPDATE', 'RESERVATION_UPDATE'),
         ('APPOINTMENT_UPDATE', 'APPOINTMENT_UPDATE'),
         ('GAME_EVENT', 'GAME_EVENT'),
         ('TRANSPORTATION_UPDATE', 'TRANSPORTATION_UPDATE'),
         ('TICKET_UPDATE', 'TICKET_UPDATE'),
         ],
        string='Outside-window message tag',
        default='HUMAN_AGENT',
        help='When inbound activity is older than the window above, send with messaging_type MESSAGE_TAG '
             'using this tag. Must comply with Meta policies for the chosen tag.',
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _('Name must be unique.')),
        ('uuid_uniq', 'unique (uuid)', _('Identifier must be unique.')),
    ]

    @api.constrains('company_id', 'team_id')
    def constrains_company(self):
        for r in self:
            if r.team_id and r.team_id.company_id and r.team_id.company_id != r.company_id:
                raise ValidationError(_('CRM Team company does not apply.'))

    @api.model_create_multi
    def create(self, vals_list):
        '''Keep ``token`` filled for Messenger connectors (field is historically required globally).'''
        out = []
        for raw in vals_list:
            vals = dict(raw)
            if vals.get('connector_type') == 'facebook':
                pg = vals.get('facebook_page_access_token') or ''
                if isinstance(pg, str):
                    pg = pg.strip()
                if pg:
                    vals['token'] = pg
                elif not vals.get('token'):
                    vals['token'] = '__facebook_messenger_placeholder__'
            out.append(vals)
        return super(AcruxChatConnector, self).create(out)

    def write(self, vals):
        if self.env.context.get('acrux_fb_token_mirror'):
            return super(AcruxChatConnector, self).write(vals)
        vals = dict(vals)
        res = super(AcruxChatConnector, self).write(vals)
        if vals.get('facebook_page_access_token') is not None or vals.get('connector_type') == 'facebook':
            for rec in self.filtered(lambda x: x.connector_type == 'facebook'):
                nt = ((rec.facebook_page_access_token or '').strip() or '__facebook_messenger_placeholder__')
                if rec.token != nt:
                    super(AcruxChatConnector, rec.with_context(acrux_fb_token_mirror=True)).write({'token': nt})
        return res

    @api.model
    def default_get(self, default_fields):
        vals = super(AcruxChatConnector, self).default_get(default_fields)
        domain = [('company_id', 'in', [self.env.company.id, False])]
        vals['team_id'] = self.env['crm.team'].search(domain, limit=1).id
        return vals

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.team_id.company_id.id != self.company_id.id:
            self.team_id = False

    @api.depends('color')
    def _compute_border_color(self):
        # buscar "$o-colors: " en .scss
        colors = ['#FFFFFF', '#F06050', '#F4A460', '#F7CD1F', '#6CC1ED', '#814968', '#EB7E7F',
                  '#2C8397', '#475577', '#D6145F', '#30C381', '#9365B8']
        for record in self:
            record.border_color = colors[record.color or 0]

    @api.depends('odoo_url', 'uuid')
    def compute_webhook_url(self):
        for record in self:
            if record.odoo_url and record.uuid:
                record.webhook_url = '%s/acrux_webhook/whatsapp_connector/%s' % \
                                     (record.odoo_url.rstrip('/'), record.uuid)
            else:
                record.webhook_url = False

    @api.depends('webhook_url', 'facebook_verify_token', 'connector_type', 'uuid')
    def _compute_facebook_webhook_help(self):
        for rec in self:
            if rec.is_facebook():
                vt = Markup('&mdash;')
                if rec.facebook_verify_token:
                    vt = Markup.escape(rec.facebook_verify_token)
                url = Markup.escape(rec.webhook_url or _('(set Odoo URL and Account ID)'))
                cid = Markup.escape(rec.uuid or _('(unset)'))
                rec.facebook_webhook_help = Markup(
                    '<div class="alert alert-info mb-3" role="alert">'
                    '<p><strong>%s</strong></p>'
                    '<ol>'
                    '<li>%s <code>%s</code></li>'
                    '<li>%s <code>%s</code></li>'
                    '<li>%s (<code>%s</code>). </li>'
                    '<li>%s <code>%s</code>, <code>%s</code>, '
                    '%s <code>%s</code>.</li>'
                    '</ol>'
                    '<p>%s</p>'
                    '</div>'
                ) % (
                    _('Facebook Messenger webhook (Meta Developers)'),
                    _('Callback URL:'),
                    url,
                    _('Verify token:'),
                    vt,
                    _('Account ID in this form is appended to your Callback URL path'),
                    cid,
                    _('Subscribe your Page to webhook fields'),
                    _('messages'),
                    _('messaging_postbacks'),
                    _('and optionally'),
                    _('messaging_optins'),
                    _('Configure the Callback URL exactly as shown; use HTTPS and a public reachable Odoo base URL.'),
                )
            else:
                rec.facebook_webhook_help = False

    @api.onchange('connector_type')
    def _onchange_connector_type_fb(self):
        if self.is_facebook():
            ver = (self.facebook_graph_api_version or 'v21.0').strip().strip('/')
            self.endpoint = 'https://graph.facebook.com/%s' % ver
        elif self.is_instagram():
            self.endpoint = 'https://social.acruxlab.net/prod/v1/in'
        elif self.is_waba_extern():
            self.endpoint = 'https://social.acruxlab.net/prod/v1/wa_ext'
        elif self.is_baileys():
            self.endpoint = self.DEFAULT_BAILEYS_GATEWAY_URL
        else:
            self.endpoint = 'https://api.acruxlab.net/prod/v2/odoo'

    @api.onchange('facebook_graph_api_version')
    def _onchange_facebook_graph_api_version_endpoint(self):
        if self.connector_type == 'facebook' and self.facebook_graph_api_version:
            ver = (self.facebook_graph_api_version or '').strip().strip('/')
            if ver:
                self.endpoint = 'https://graph.facebook.com/%s' % ver

    @api.model
    def execute_maintenance(self, days=21):
        ''' Call from cron.
            Delete attachment older than N days. '''
        Message = self.env['acrux.chat.message']
        date_old = datetime.now() - timedelta(days=int(days))
        date_old = date_old.strftime(DEFAULT_SERVER_DATE_FORMAT)
        mess_ids = Message.search([('res_model', '=', 'ir.attachment'),
                                   ('res_id', '!=', False),
                                   ('date_message', '<', date_old)])
        attach_to_del = mess_ids.mapped('res_id')
        erased_ids = Message.unlink_attachment(attach_to_del)
        for mess_id in mess_ids:
            if mess_id.res_id in erased_ids:
                text = '%s\n(Attachment removed)' % mess_id.text
                mess_ids.write({'text': text.strip(),
                                'res_id': False})
        _logger.info('________ | execute_maintenance: Deleting %s attachments older than %s' %
                     (len(attach_to_del), date_old))

    def _get_custom_info(self):
        self.ensure_one()
        cp = self.company_id
        return {
            'odoo_url': self.odoo_url,
            'lang': cp.partner_id.lang,
            'phone': cp.phone,
            'website': cp.website,
            'currency': cp.currency_id.name,
            'country': cp.country_id.name,
            'name': cp.name,
            'email': cp.email,
        }

    def ca_set_settings(self):
        self.env.cr.commit()
        self.ensure_one()
        if self.is_facebook():
            return True
        data = {'webhook': self.webhook_url, 'info': self._get_custom_info()}
        return self.ca_request('config_set', data)

    def ca_get_chat_list(self):
        self.ensure_one()
        data = self.ca_request('contact_get_all')
        dialogs = data.get('dialogs', [])
        vals = {}
        for user in dialogs:
            phone = user.get('id', '').split('@')[0]
            name = user.get('name', '')
            image_url = user.get('image', '')
            vals[phone] = {'name': name, 'image_url': image_url}
        self.process_chat_list(vals)

    def check_is_valid_old_records(self):
        self.ensure_one()
        self.check_is_valid_old_records_ids(False)

    def check_is_valid_old_records_ids(self, check_conv_ids):
        ''' Check all records, not API '''
        self.ensure_one()
        if self.connector_type != 'apichat.io':
            raise UserError(_('Available only for Whatsapp connector through apichat.io.'))
        domain = [('connector_id', '=', self.id), ('last_received', '!=', False), ('valid_number', 'in', ['no', False])]
        if check_conv_ids:
            domain.append(('id', 'in', check_conv_ids.ids))
        conv_ids = self.env['acrux.chat.conversation'].search(domain)
        conv_ids.valid_number = 'yes'

    def check_is_valid_active(self):
        return bool(self.connector_type == 'apichat.io' and self.auto_valid_number)

    def check_is_valid_update(self):
        self.ensure_one()
        if not self.check_is_valid_active():
            raise ValidationError(_('You have disabled this service.'))
        ret = self.ca_get_check_number([], raise_error=False)
        error = ret.get('error')
        if error:
            ret.update({'limit': 0, 'remain_limit': 0, 'date_due': str(self.valid_date or '')})
        self.valid_limit = ret.get('limit')
        self.valid_balance = ret.get('remain_limit')
        date_due = ret.get('date_due')[:10] if ret.get('date_due') else False
        self.valid_date = fields.Date.to_date(date_due) if date_due else False
        if error:
            return self.env['acrux.chat.pop.message'].message(error)

    def check_is_valid_whatsapp_number(self, conv_ids, overwrite=True, raise_error=True):
        ''' Returns max 20 records or error '''
        self.ensure_one()
        if not self.check_is_valid_active():
            return dict()
        numbers = [x.number for x in conv_ids if x.connector_type == 'apichat.io' and x.valid_number != 'yes']
        ret = self.ca_get_check_number(numbers[:20], raise_error)
        numbers = ret.get('numbers')
        if overwrite and numbers:
            for conv_id in conv_ids:
                check = numbers.get(conv_id.number)
                if check:
                    if check['valid']:
                        conv_id.valid_number = 'yes'
                        if not check['same']:
                            conv_id.number = check['number']
                    else:
                        conv_id.valid_number = 'no'
        return ret

    def ca_get_check_number(self, list_numbers, raise_error=True):
        ''' Returns max 20 records '''
        self.ensure_one()
        conn_id = self.validate_conn_id or self
        res = dict()
        if conn_id.connector_type != 'apichat.io':
            raise UserError(_('Available only for Whatsapp connector through apichat.io.'))
        txt_numbers = ''
        count = 0
        for n in list_numbers:
            x = self.clean_id(n)
            if x:
                count += 1
                txt_numbers += '%s,' % x
        if count > 20:
            raise UserError('max. 20 numbers')
        params = {'numbers': txt_numbers.strip(',')}
        try:
            datas = conn_id.ca_request('whatsapp_number_get', params=params, timeout=30)
            remain = datas.get('remain_limit', 0)
            numbers = datas.get('numbers', [])
        except ValidationError as _e:
            error = str(_e)
            reached = _('You reached the limit of your Validation Plan.')
            expired = _('Your Validation Plan has expired or not exist.')
            if error == 'You reached your package limit.':
                error = reached
            elif error == 'Your package is expired.':
                error = expired
            elif error == 'You have not contracted this package.':
                error = expired
            if raise_error:
                raise ValidationError(error)
            else:
                return {'error': error}
        for n in numbers:
            res[n['id']] = {'valid': bool(n['whatsapp_id'] or ''),
                            'same': bool(n['id'] == n['whatsapp_id']),
                            'number': n['whatsapp_id']}
        _logger.info('*check_number*\n%s' % res)
        return {'numbers': res,
                'remain_limit': remain,
                'date_due': datas.get('date_due', False),
                'limit': datas.get('limit', 0)}

    def process_chat_list(self, vals):
        self.ensure_one()
        Conversation = self.env['acrux.chat.conversation']
        for conv in Conversation.search([('image_128', '=', False)]):
            if conv.number in vals:
                image_url = vals[conv.number].get('image_url', '')
                if image_url and image_url.startswith('http'):
                    raw_image = get_image_from_url(image_url)
                    conv.image_128 = raw_image

    def ca_set_logout(self):
        self.ensure_one()
        self.ca_request('status_logout', timeout=20)
        self.ca_status = False
        self.ca_qr_code = False

    def ca_get_status(self):
        ''' API: {'status': {'acrux_ok': 'texto a mostrar'
                             ó 'acrux_er': 'texto a mostrar'
                             ó dict apichat.io}
                 }
        '''
        self.ensure_one()
        if self.connector_type == 'not_set':
            raise ValidationError(_('"Connect to" is not set, check out your config.'))
        Pop = self.env['acrux.chat.pop.message']
        if self.is_facebook():
            return self._facebook_ca_get_status()
        if self.uses_acrux_social_gateway():
            self.ca_qr_code = False
            params = {
                'webhook': self.webhook_url,
                'lang': self.env.context.get('lang', 'en'),
            }
            data = self.ca_request('status', timeout=20, params=params)
            message, detail, redirectData = self.process_facebook_get_status(data)
            return Pop.message(message, detail) if message else redirectData
        message = detail = False
        self.ca_qr_code = False
        data = self.ca_request('status_get', timeout=20)
        status = data.get('status', {})
        acrux_ok = status.get('acrux_ok')
        acrux_er = status.get('acrux_er')
        accountStatus = status.get('accountStatus')
        if acrux_ok:
            self.ca_status = True
            self.message = acrux_ok
            message = 'Status'
            detail = acrux_ok
            self.ca_set_settings()
        elif acrux_er:
            self.ca_status = False
            self.message = acrux_er
            message = 'Status'
            detail = acrux_er
        elif accountStatus:
            qrCode = status.get('qrCode')
            if accountStatus == 'authenticated':
                self.ca_status = True
                self.message = False
                message = 'All good!'
                detail = 'WhatsApp connects to your phone to sync messages. ' \
                         'To reduce data usage, connect your phone to Wi-Fi.'
                self.ca_set_settings()
            elif accountStatus == 'got qr code':
                self.ca_status = False
                if qrCode:
                    self.ca_qr_code = qrCode.split('base64,')[1]
                    self.message = 'Please Scan QR code'
                else:
                    message = 'An unexpected error occurred. Please try again.'
                    self.message = message
            else:
                self.ca_status = False
                self.message = 'An unexpected error occurred. Please try again.'
                statusData = status.get('statusData')
                title = statusData.get('title')
                msg = statusData.get('msg')
                substatus = statusData.get('substatus')
                message = 'Status: %s' % (substatus or '-')
                detail = '<b>%s</b><br/>%s' % (title, msg)
        return Pop.message(message, detail) if message else True

    def ca_status_change(self, status):
        self.ensure_one()
        if status == 'connected':
            if not self.ca_status:
                self.ca_status = True
                self.ca_qr_code = False
                self.message = False
        elif status == 'disconnected':
            if self.ca_status:
                self.ca_status = False
                self.message = False

    def response_handler(self, req):
        self.ensure_one()
        error = False
        ret = {}
        if self.uses_acrux_social_gateway():
            if req.status_code == 200:
                try:
                    out = req.json()
                except ValueError:
                    out = {}
            else:
                log_request_error([req.text or req.reason], req)
                raise ValidationError(req.text or req.reason)
            return out
        try:
            ret = req.json()
        except ValueError:
            pass
        if req.status_code == 200:
            pass
        else:
            error = self.get_request_error_message(req, ret)
        if error:
            log_request_error([error], req)
            raise ValidationError(error)
        return ret

    def get_request_error_message(self, req, ret):
        ''' Estado respuesta:
                200        Ok (el resto hace raise)
                202        Accepted (error en el proveedor o cuenta impaga)
                204        No Content (método o parámetro no implementado para este conector)
                400        Bad request. Please pass a valid value in the parameters.
                403        Forbidden. Invalid authentication.
                404        Not found.
                500        Internal server error. (error en lambda)
            :param requests.Response req: request
            :return dict
        '''
        error = False
        if req.status_code == 202:
            error = ret.get('error', '3rd party connector error. Please try again or check configuration.')
        elif req.status_code == 204:
            error = ret.get('error', '3rd party connector not implement this option.')
        elif req.status_code == 400:
            error = ret.get('error', 'Bad request. Please pass a valid value in the parameters.')
        elif req.status_code == 403:
            error = ret.get('error', 'Forbidden. Invalid authentication.')
        elif req.status_code == 404:
            error = ret.get('error', 'Connector URL not found. Please set correctly.')
        elif req.status_code == 500:
            error = ret.get('error', 'Internal server error. Please try again.')
        else:
            error = ret.get('error', 'Unknown error.')
        return error

    def get_headers(self, path=''):
        self.ensure_one()
        return {
            'Accept': 'application/json',
            'token': self.token,
            'client_id': self.uuid,
            'action': path,
            'Content-Type': 'application/json'
        }

    def get_api_url(self, path=''):
        self.ensure_one()
        if self.uses_acrux_social_gateway():
            return '%s/%s' % (self.endpoint.strip('/'), path)
        return self.endpoint.strip('/')

    def get_actions(self):
        self.ensure_one()
        actions = {}
        if self.uses_acrux_social_gateway():
            actions = self.get_acrux_social_actions()
        else:
            actions = {
                'send': 'post',
                'msg_set_read': 'post',
                'config_get': 'get',
                'config_set': 'post',
                'status_get': 'get',
                'status_logout': 'post',
                'contact_get': 'get',
                'contact_get_all': 'get',
                'init_free_test': 'post',
                'whatsapp_number_get': 'get',
                'template_get': 'get',
                'opt_in': 'post',
            }
        actions['delete_message'] = 'delete'
        return actions

    def get_acrux_social_actions(self):
        return {
            'status': 'get',
            'config': 'post',
            'contact': 'get',
            'logout': 'post',
            'readChat': 'post',
            'sendMessage': 'post',
            'templates': 'get',
        }

    def get_req_method(self, action):
        actions = self.get_actions()
        if action not in actions:
            raise ValidationError(_('Action %s is not implemented.') % action)
        return actions[action]

    def hook_request_args(self, args):
        self.ensure_one()
        if args['headers']['action'] == 'status_logout':
            args['data'] = json.dumps({})  # backwards compatibility
        return args

    def ca_request(self, path, data={}, params={}, timeout=False, ignore_exception=False):
        self.ensure_one()
        if self.is_facebook():
            result = {}
            timeout = timeout or TIMEOUT
            try:
                return self._facebook_ca_request(path, data=data, params=params, timeout=timeout,
                                                   ignore_exception=ignore_exception)
            except (requests.exceptions.SSLError,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.HTTPError,
                    requests.exceptions.RequestException,
                    requests.exceptions.ConnectionError):
                if not ignore_exception:
                    raise
                return result
        if self.uses_acrux_social_gateway():
            path = self.get_acrux_social_api_path(path)
            if path is None:
                return
        method = self.get_req_method(path)
        result = {}
        timeout = timeout or TIMEOUT
        url = self.get_api_url(path)
        headers = self.get_headers(path)
        req = False
        try:
            args = {
                'url': url,
                'headers': headers,
                'timeout': timeout,
                'verify': self.verify,
            }
            if data:
                args['data'] = json.dumps(data)
            if params:
                args['params'] = params
            self.log_data(method, url, params, data, headers)
            args = self.hook_request_args(args)
            req = getattr(requests, method)(**args)
            result = self.response_handler(req)
        except requests.exceptions.SSLError:
            if not ignore_exception:
                log_request_error(['SSLError', method, path, params, data])
            raise UserError(_('Error! Could not connect to server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout:
            if not ignore_exception:
                log_request_error(['ConnectTimeout', method, path, params, data])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError):
            if not ignore_exception:
                log_request_error(['requests', method, path, params, data])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Could not connect to your account.\nPlease check API Endpoint Url.\n%s') % ex_type)
        self.log_result(method, url, result, params, data, req)
        return result

    def log_data(self, req_type, url, param, data, header):
        pass

    def log_result(self, req_type, url, result, param, data, req):
        pass

    def init_free_test(self):
        self.ensure_one()
        data = self._get_custom_info()
        self.uuid = 'test_demo_chat_api'  # backwards compatibility
        self.endpoint = 'http://localhost:3000'  # backwards compatibility
        data.update({'tz': self.env.user.tz})
        result = self.ca_request('init_free_test', data)
        connector_type = result.get('connector_type')
        if connector_type:
            self.connector_type = connector_type
        if result.get('token'):
            self.token = result.get('token')
        if result.get('uuid'):
            self.uuid = result.get('uuid')
        self.ca_status = False
        self.ca_qr_code = False
        self.message = False

    def init_free_test_wizard(self):
        self.ensure_one()
        # if '//localhost' in self.odoo_url or '//127.0.' in self.odoo_url:
        #     raise UserError(_("Please set 'Odoo Url (WebHook)'.\n"
        #                       "You are working on 'localhost', you will not be able to receive messages!"))
        return {
            'name': _('Init Free Test'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'init.free.test.wizard',
            'target': 'new',
            'context': dict(default_connector_id=self.id)
        }

    @api.model
    def init_free_test_record(self):
        if not self.search_count([]):
            self.create({
                'name': 'Free Test (apichat.io)',
                'connector_type': 'apichat.io',
                'source': '/',
                'uuid': 'free_test_account',
                'token': '123456',
                'tz': self.env.ref('base.user_admin').tz or 'UTC',
            })

    def action_ca_get_status(self):
        self.ensure_one()
        ret = self.ca_get_status()
        if not self.ca_status and self.ca_qr_code:
            return {
                'name': _('Scan QR code'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'acrux.chat.connector.scanqr.wizard',
                'target': 'new',
                'context': dict(default_connector_id=self.id)
            }
        else:
            return ret

    def assert_id(self, key):
        self.ensure_one()
        if not self.env.context.get('from_webhook') and not self.is_facebook_or_instagram():
            if key != self.clean_id(key):
                raise ValidationError(_('Invalid number'))
            phone_format(key, formatted=False)  # to check

    def clean_id(self, key):
        self.ensure_one()
        if self.is_facebook_or_instagram():
            return key
        return clean_number(key)

    def format_id(self, key):
        self.ensure_one()
        if self.is_facebook():
            return 'Facebook'
        elif self.is_instagram():
            return 'Instagram'
        simple = '+%s' % clean_number(key)
        formatted = phone_format(key, formatted=True, raise_error=False)
        reverse = '+%s' % clean_number(formatted)
        return formatted if simple == reverse else simple

    def allow_caption(self):
        self.ensure_one()
        if self.uses_acrux_social_gateway():
            return self.is_waba_extern()
        return True

    def update_template_waba(self):
        data = self.ca_request('template_get')
        Template = self.env['acrux.chat.template.waba']
        Template.create_or_update(data, self)
        return self.env['acrux.chat.pop.message'].message(_('Templates updated.'))

    def get_url_from_attachment(self, attach_id):
        self.ensure_one()
        access_token = attach_id.generate_access_token()[0]
        url = '/web/chatresource/%s/%s' % (attach_id.id, access_token)
        base_url = self.odoo_url.rstrip('/')
        return base_url.rstrip('/') + url

    def get_url_from_model_field(self, record, field):
        hash_id = hashlib.sha1(str((record.write_date or record.create_date or '')).encode('utf-8'))
        hash_id = hash_id.hexdigest()[0:7]
        url = '/web/static/chatresource/%s/%s_%s/%s' % (record._name, record.id, hash_id, field)
        base_url = self.odoo_url.rstrip('/')
        return base_url.rstrip('/') + url

    def _compute_hide_branding(self):
        hide_branding = self.env['ir.config_parameter'].sudo().get_param('chatroom.hide.branding', 'False') == 'True'
        for record in self:
            record.chatroom_hide_branding = hide_branding

    def facebook_graph_root(self):
        """Base URL ``https://graph.facebook.com/<version>`` (no trailing slash)."""
        self.ensure_one()
        ver = (self.facebook_graph_api_version or 'v21.0').strip().strip('/')
        return 'https://graph.facebook.com/%s' % ver

    def facebook_get_outbound_messaging_params(self, conversation):
        '''Return dict with messaging_type (RESPONSE|MESSAGE_TAG) and optional Meta ``tag`` string.'''
        self.ensure_one()
        if self.connector_type != 'facebook':
            return {'messaging_type': 'RESPONSE', 'tag': None}
        hrs = float(self.facebook_messenger_window_hours or 24)
        if hrs < 1:
            hrs = 23.917
        last_in = conversation.last_received
        if last_in:
            secs = abs((fields.Datetime.now() - last_in).total_seconds())
            if secs < hrs * 3600:
                return {'messaging_type': 'RESPONSE', 'tag': None}
        tag = self.facebook_outside_window_message_tag or 'none'
        if tag and tag != 'none':
            return {'messaging_type': 'MESSAGE_TAG', 'tag': tag}
        return {'messaging_type': 'RESPONSE', 'tag': None}

    def facebook_verify_hub_signature256(self, raw_body, signature_header):
        """Verify ``X-Hub-Signature-256`` from Meta webhook. Skip if ``facebook_app_secret`` is empty."""
        self.ensure_one()
        secret = (self.facebook_app_secret or '').strip()
        if not secret:
            return True
        if not signature_header or not signature_header.startswith('sha256='):
            return False
        expect = signature_header.split('=', 1)[1]
        digest = hmac.new(
            secret.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, expect)

    def _facebook_graph_error_message(self, err):
        if not err:
            return _('Facebook returned an unknown error.')
        return err.get('message') or _('Facebook returned an unknown error.')

    def _facebook_request(self, graph_path, method='get', json_body=None, extra_params=None, timeout=None):
        self.ensure_one()
        token = (self.facebook_page_access_token or '').strip()
        if not token:
            raise UserError(_('Missing Facebook Page Access Token.'))
        method = method.lower()
        timeout = timeout or TIMEOUT
        url = '%s/%s' % (self.facebook_graph_root(), graph_path.strip('/'))
        params = {'access_token': token}
        if extra_params:
            params.update(extra_params)
        try:
            if method == 'get':
                r = requests.get(url, params=params, timeout=timeout, verify=self.verify)
            elif method == 'post':
                r = requests.post(url, params=params, json=json_body, timeout=timeout, verify=self.verify)
            elif method == 'delete':
                r = requests.delete(url, params=params, json=json_body, timeout=timeout, verify=self.verify)
            else:
                raise ValidationError(_('Unsupported HTTP method for Facebook'))
        except requests.exceptions.RequestException as exc:
            log_request_error([str(exc), graph_path, extra_params, json_body])
            raise UserError(_('Could not reach Facebook. %s') % exc) from exc

        body = {}
        try:
            body = r.json() if r.content else {}
        except ValueError:
            body = {}
        err = body.get('error')
        if isinstance(err, dict) and err.get('message'):
            raise UserError('%s (%s)' % (
                self._facebook_graph_error_message(err),
                err.get('code', ''),
            ))
        if not r.ok:
            raise UserError(_('Facebook error (HTTP %s).') % r.status_code)
        return body

    def _facebook_ca_get_status(self):
        """Validate Page token and optionally remind about webhook verification setup."""
        self.ensure_one()
        Pop = self.env['acrux.chat.pop.message']
        self.ca_qr_code = False
        verify_tok = (self.facebook_verify_token or '').strip()
        page_tok = (self.facebook_page_access_token or '').strip()
        if not verify_tok:
            self.ca_status = False
            detail = _('Set a Webhook Verify Token (matches Meta Developers) '
                       'before completing webhook subscription.')
            self.message = detail
            return Pop.message(_('Incomplete'), detail)
        if not page_tok:
            self.ca_status = False
            detail = _('Set the Page Access Token from Meta Business settings.')
            self.message = detail
            return Pop.message(_('Incomplete'), detail)
        data = self._facebook_request(
            'me',
            method='get',
            extra_params={'fields': 'id,name'},
            timeout=20,
        )
        self.ca_status = True
        self.message = _('Connected.')
        name = data.get('name') or _('Page')
        return Pop.message(_('Connected'), _('Messenger Page: %s') % Markup.escape(name))

    def _facebook_ca_request(self, path, data, params, timeout, ignore_exception=False):
        """Outbound actions for Messenger (send, typing indicators, fetch profile)."""
        self.ensure_one()
        to = timeout or TIMEOUT
        if path == 'send':
            mid = self._facebook_send_via_graph(data)
            if not mid:
                raise ValidationError(_('Facebook did not return a message id.'))
            return {'msg_id': mid}
        if path == 'msg_set_read':
            psid = ''
            if isinstance(data, dict):
                psid = (data.get('phone') or data.get('recipient') or '').strip()
            if psid:
                try:
                    self._facebook_request(
                        'me/messages',
                        method='post',
                        json_body={'recipient': {'id': psid}, 'sender_action': 'mark_seen'},
                        timeout=to,
                    )
                except UserError as err:
                    if ignore_exception:
                        _logger.info('Facebook msg_set_read (mark_seen) skipped: %s', err.args[0] if err.args else err)
                        return {}
                    raise
                except Exception as err:
                    if ignore_exception:
                        _logger.info('Facebook msg_set_read (mark_seen) skipped: %s', err, exc_info=True)
                        return {}
                    raise
            return {}
        if path == 'contact_get':
            psid = ''
            if isinstance(params, dict):
                psid = str(params.get('chatId') or '').strip()
            if isinstance(data, dict) and not psid:
                psid = str(data.get('chatId') or '').strip()
            if not psid:
                return {}
            profile = {}
            try:
                profile = self._facebook_request(
                    psid,
                    method='get',
                    extra_params={
                        'fields': 'first_name,name,profile_pic,picture.width(720).height(720)',
                    },
                    timeout=to,
                )
            except UserError:
                return {}
            name = profile.get('name') or profile.get('first_name') or ''
            pic = profile.get('profile_pic') or (profile.get('picture') or {}).get('data', {}).get('url')
            out = {'name': name.strip() or False}
            if pic:
                out['image'] = pic
            return out
        return {}

    def _facebook_attachment_url_with_token(self, url):
        tok = (self.facebook_page_access_token or '').strip()
        if not tok or not url:
            return url
        sep = '&' if ('?' in url) else '?'
        return '%s%saccess_token=%s' % (url, sep, quote(tok, safe=''))

    def _facebook_post_outbound_shell(self, recipient_id, messaging_type, message_tag, message_inner, timeout):
        """Single ``POST me/messages`` with optional MESSAGE_TAG."""
        fb_body = {
            'recipient': {'id': recipient_id},
            'messaging_type': messaging_type,
            'message': message_inner,
        }
        if messaging_type.upper() == 'MESSAGE_TAG' and message_tag:
            fb_body['tag'] = message_tag
        return self._facebook_request(
            'me/messages',
            method='post',
            json_body=fb_body,
            timeout=timeout,
        )

    def _facebook_send_via_graph(self, payload):
        """Build Messenger send payload from ChatRoom ``message_parse`` structure."""
        self.ensure_one()
        recipient_id = payload.get('to')
        if not recipient_id:
            raise ValidationError(_('Missing Messenger recipient.'))
        msg_type = payload.get('type')
        messaging_type = (payload.get('messaging_type') or 'RESPONSE').upper()
        message_tag = payload.get('message_tag')
        qr_raw = payload.get('fb_quick_replies') or []
        qr = qr_raw[:13] if isinstance(qr_raw, list) else []
        generic = payload.get('fb_generic_template')
        quoted = payload.get('quote_msg_id') or payload.get('reply_msg_id')
        caption = ((payload.get('text') or '')).strip()
        reply_mid = quoted if quoted else False

        def post(msg_inner, timeout=None):
            to = timeout or TIMEOUT
            resp = self._facebook_post_outbound_shell(
                recipient_id, messaging_type, message_tag, msg_inner, to,
            )
            mid = resp.get('message_id')
            return mid if isinstance(mid, str) else (str(mid) if mid else '')

        # URL / Phone buttons → generic template (no quick replies mixed — enforced earlier)
        if generic:
            tmpl_msg = {'attachment': {'type': 'template', 'payload': generic}}
            return post(tmpl_msg)

        if msg_type == 'text':
            text_body = caption[:1999]
            msg = {'text': text_body}
            if qr:
                msg['quick_replies'] = qr
            if reply_mid and msg.get('text'):
                msg['reply_to'] = {'mid': str(reply_mid)}
            return post(msg)

        if msg_type in ('image', 'video', 'audio', 'file'):
            att_kind = msg_type if msg_type != 'file' else 'file'
            attachment_url = payload.get('url')
            if not attachment_url:
                raise ValidationError(_('Attachment URL missing for outbound message.'))
            if caption:
                cap_msg = {'text': caption[:1999]}
                if reply_mid:
                    cap_msg['reply_to'] = {'mid': str(reply_mid)}
                    reply_mid = False
                post(cap_msg)
            attach_inner = {
                'attachment': {
                    'type': att_kind,
                    'payload': {'url': attachment_url, 'is_reusable': True},
                }
            }
            if qr:
                attach_inner['quick_replies'] = qr
            if reply_mid:
                attach_inner['reply_to'] = {'mid': str(reply_mid)}
            return post(attach_inner)

        if msg_type == 'location':
            addr = payload.get('address') or ''
            lat = payload.get('latitude')
            lng = payload.get('longitude')
            msg = {'text': '%s%s%s,%s' % (addr.strip(), '\n' if addr else '', lat or '', lng or '')[:1999]}
            if qr:
                msg['quick_replies'] = qr
            if reply_mid and msg.get('text'):
                msg['reply_to'] = {'mid': str(reply_mid)}
            return post(msg)

        raise ValidationError(_('Message type "%s" is not supported over Facebook Messenger.') % msg_type)

    def _facebook_format_fallback_text_attachment(self, att_type, fb_payload):
        if att_type == 'location':
            coords = fb_payload.get('coordinates', {}) or fb_payload or {}
            lat = coords.get('lat')
            lng = coords.get('long')
            return '\n'.join(filter(None, [_('Location'), str(lat), str(lng)]))
        if att_type == 'fallback':
            return fb_payload.get('title') or fb_payload.get('url') or att_type
        return _('[Attachment: %s]') % att_type

    def facebook_dispatch_webhook(self, payload):
        """Split Meta ``object=page`` JSON into normalized Baileys-style dicts for the work queue."""
        self.ensure_one()

        def make_msg_uid(base_mid, suffix):
            b = base_mid.strip() if isinstance(base_mid, str) else ''
            if b:
                return '%s__%s' % (b, suffix)
            return ''

        entries = payload.get('entry') if isinstance(payload, dict) else None
        jobs = []
        if not isinstance(entries, list):
            return jobs
        page_filter = str(self.facebook_page_id).strip() if self.facebook_page_id else ''
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            eid = str(entry.get('id') or '').strip()
            if page_filter and eid and eid != page_filter:
                continue
            messaging = entry.get('messaging') or []
            if not isinstance(messaging, list):
                continue
            for evt in messaging:
                ts = unix_ts_to_naive_utc((evt.get('timestamp') or 0) / 1000)
                ts_str = ts.isoformat() if ts else ''
                if evt.get('message'):
                    m = evt['message']
                    if m.get('is_echo'):
                        continue
                    quote_id = ''
                    qr = m.get('reply_to') or {}
                    if isinstance(qr, dict):
                        quote_id = qr.get('mid') or ''
                    mid = (m.get('mid') or m.get('message_id')) or ''
                    sender_psid = (evt.get('sender') or {}).get('id') or ''
                    if not sender_psid:
                        continue
                    attachments = m.get('attachments') if isinstance(m.get('attachments'), list) else []
                    caption = (m.get('text') or '').strip()

                    def base_row(msg_uid_suffix, msg_id_override=''):
                        return {
                            'name': '',
                            'number': sender_psid,
                            'id': msg_id_override or make_msg_uid(mid, msg_uid_suffix),
                            'time': ts,
                            'conv_type': 'normal',
                            'quote_msg_id': quote_id or False,
                            'metadata': m.get('metadata'),
                        }

                    if caption and attachments:
                        jobs.append({'ttype': 'in_message', 'data': dict(
                            {'type': 'text', 'txt': caption}, **base_row('txt'))})
                    elif caption and not attachments:
                        jobs.append({'ttype': 'in_message', 'data': dict(
                            {'type': 'text', 'txt': caption}, **base_row('msg'))})

                    if not attachments:
                        continue

                    for idx, att in enumerate(attachments):
                        suffix = 'att%s' % idx
                        row = base_row(suffix if len(attachments) > 1 else 'att')

                        att_type = (att.get('type') or '').lower()
                        fb_pl = att.get('payload') or {}
                        mapped = {
                            'image': 'image', 'video': 'video', 'audio': 'audio', 'file': 'file',
                            'share': 'file', 'fallback': 'file', 'sticker': 'sticker',
                            'location': 'location',
                        }.get(att_type, 'text')

                        url_part = fb_pl.get('url')

                        if mapped == 'location':
                            coords = fb_pl.get('coordinates') if isinstance(fb_pl.get('coordinates'), dict) else {}
                            lt = coords.get('lat') or fb_pl.get('lat')
                            lg = coords.get('long') or fb_pl.get('long')
                            loc_txt = self._facebook_format_fallback_text_attachment('location', fb_pl)
                            jobs.append({'ttype': 'in_message', 'data': dict({
                                'type': 'location',
                                'txt': loc_txt or caption,
                                'address': caption or loc_txt,
                                'latitude': str(lt or ''),
                                'longitude': str(lg or ''),
                            }, **row)})
                            continue

                        if mapped == 'text' or not url_part:
                            txt_val = caption or self._facebook_format_fallback_text_attachment(att_type, fb_pl)
                            jobs.append({'ttype': 'in_message', 'data': dict({'type': 'text', 'txt': txt_val}, **row)})
                            continue

                        dl_url = self._facebook_attachment_url_with_token(url_part)
                        fname = fb_pl.get('title') or '%s_attachment' % (att_type or 'file')
                        kind = mapped if mapped not in ('text',) else 'file'
                        jobs.append({'ttype': 'in_message', 'data': dict({
                            'type': kind,
                            'txt': caption,
                            'url': dl_url,
                            'filename': fname,
                        }, **row)})

                elif evt.get('postback'):
                    pb = evt['postback']
                    sender_psid = (evt.get('sender') or {}).get('id') or ''
                    if not sender_psid:
                        continue
                    pb_mid = pb.get('mid') or pb.get('message', {}).get('mid') if isinstance(pb.get('message'), dict) else ''
                    jobs.append({'ttype': 'in_message', 'data': {
                        'type': 'text',
                        'txt': (pb.get('title') or pb.get('payload') or ''),
                        'name': '',
                        'number': sender_psid,
                        'id': pb_mid or '',
                        'time': ts_str,
                        'conv_type': 'normal',
                        'quote_msg_id': False,
                    }})

        return jobs

    def get_acrux_social_api_path(self, path):
        if path == 'config_set':
            path = 'config'
        elif path == 'contact_get':
            path = 'contact'
        elif path == 'send':
            path = 'sendMessage'
        elif path == 'msg_set_read':
            if self.is_instagram():  # instagram no soporta marcar como leido
                path = None
            else:
                path = 'readChat'
        elif path == 'status_logout':
            path = 'logout'
        elif path == 'template_get':  # facebook e instagram no soprotan
            path = 'templates' if self.is_waba_extern() else None
        return path

    def process_facebook_get_status(self, data):
        self.ensure_one()
        message = detail = False
        redirectData = True
        if 'is_connected' in data:
            if data['is_connected']:
                detail = _('Connected.')
                message = 'Status'
                self.ca_status = True
                self.message = detail
                self.ca_set_settings()
            else:
                message = 'Status'
                detail = data.get('reason', _('An unexpected error occurred'))
                self.ca_status = False
                self.message = detail
        elif 'url' in data:
            redirectData = {
                'type': 'ir.actions.act_url',
                'url': data['url'],
                'target': 'self',
            }
        else:
            self.ca_status = False
            message = 'An unexpected error occurred. Please try again.'
            self.message = message
        return message, detail, redirectData

    def is_facebook_or_instagram(self):
        return self.connector_type in ['facebook', 'instagram']

    def uses_acrux_social_gateway(self):
        """Instagram / WhatsApp External use Acrux social proxy; Meta Page Messenger uses Graph directly."""
        return self.connector_type in ('instagram', 'waba_extern')

    def is_facebook(self):
        return self.connector_type == 'facebook'

    def is_instagram(self):
        return self.connector_type == 'instagram'

    def is_waba_extern(self):
        return self.connector_type == 'waba_extern'

    def is_baileys(self):
        return self.connector_type == 'baileys'

    def uses_whatsapp_web_api(self):
        """Same outbound API as ApiChat.io (single base URL, ``action`` in headers)."""
        self.ensure_one()
        return self.connector_type in ('apichat.io', 'baileys')
