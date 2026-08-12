# -*- coding: utf-8 -*-
"""
Facebook Page connect flow.

Client side (static/src/js/facebook_connect.js) loads the Facebook JS SDK
using the App ID from Settings, pops the Facebook Login dialog with the
scopes needed to manage Page messaging, and gets back a short-lived USER
access token. That token alone is not enough to receive/send messages -
these two endpoints do the rest server-side (where the App Secret can
safely be used):

  1. /omni/connect/facebook/pages
     short-lived user token -> long-lived user token -> list of Pages the
     user manages, each with its own (already long-lived) Page Access
     Token from /me/accounts, plus any linked Instagram Business Account.

  2. /omni/connect/facebook/connect_page
     For one chosen Page: create/update the crm.channel record AND call
     POST /{page-id}/subscribed_apps so the Page actually starts sending
     webhook events to us - this is the step people most often forget to
     do by hand, and it's why "the token is right but nothing arrives"
     happens.

Both require an Odoo backend session (auth='user') - this is an admin
screen, not a public endpoint. The Meta App ID/Secret never leave the
server.
"""
import logging

import requests

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

GRAPH_VERSION = 'v19.0'
GRAPH_BASE = f'https://graph.facebook.com/{GRAPH_VERSION}'


class ConnectCenterController(http.Controller):

    def _app_credentials(self):
        icp = request.env['ir.config_parameter'].sudo()
        app_id = icp.get_param('crm_omnichannel_connect_center.meta_app_id')
        app_secret = icp.get_param('crm_omnichannel_connect_center.meta_app_secret')
        verify_token = icp.get_param('crm_omnichannel_connect_center.meta_verify_token')
        return app_id, app_secret, verify_token

    @http.route('/omni/connect/facebook/pages', type='json', auth='user', methods=['POST'])
    def facebook_list_pages(self, access_token=None, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            return {'ok': False, 'error': _('Only administrators can connect channels.')}
        if not access_token:
            return {'ok': False, 'error': _('Missing Facebook access token.')}

        app_id, app_secret, __ = self._app_credentials()
        if not (app_id and app_secret):
            return {'ok': False, 'error': _('Set the Meta App ID and App Secret in Settings first.')}

        try:
            # Exchange the short-lived user token from the JS SDK for a
            # long-lived one, so the resulting Page tokens don't expire
            # in an hour.
            exch = requests.get(f'{GRAPH_BASE}/oauth/access_token', params={
                'grant_type': 'fb_exchange_token',
                'client_id': app_id,
                'client_secret': app_secret,
                'fb_exchange_token': access_token,
            }, timeout=15).json()
            if 'error' in exch:
                return {'ok': False, 'error': exch['error'].get('message', 'Token exchange failed')}
            long_lived_token = exch.get('access_token', access_token)

            pages_resp = requests.get(f'{GRAPH_BASE}/me/accounts', params={
                'access_token': long_lived_token,
                'fields': 'id,name,access_token,instagram_business_account{id,username}',
            }, timeout=15).json()
            if 'error' in pages_resp:
                return {'ok': False, 'error': pages_resp['error'].get('message', 'Could not list Pages')}
        except requests.exceptions.RequestException as e:
            return {'ok': False, 'error': _('Could not reach Facebook: %s') % e}

        pages = []
        for page in pages_resp.get('data', []):
            ig = page.get('instagram_business_account') or {}
            pages.append({
                'id': page['id'],
                'name': page['name'],
                'access_token': page['access_token'],
                'instagram_id': ig.get('id'),
                'instagram_username': ig.get('username'),
            })
        return {'ok': True, 'pages': pages}

    @http.route('/omni/connect/facebook/connect_page', type='json', auth='user', methods=['POST'])
    def facebook_connect_page(self, page_id=None, page_name=None, page_access_token=None,
                               instagram_id=None, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            return {'ok': False, 'error': _('Only administrators can connect channels.')}
        if not (page_id and page_access_token):
            return {'ok': False, 'error': _('Missing page_id or page_access_token.')}

        app_id, app_secret, verify_token = self._app_credentials()
        if not app_secret:
            return {'ok': False, 'error': _('Set the Meta App Secret in Settings first.')}

        # Auto-subscribe the app to this Page's webhook events - the step
        # that's easiest to forget when doing this by hand.
        try:
            sub = requests.post(f'{GRAPH_BASE}/{page_id}/subscribed_apps', params={
                'access_token': page_access_token,
                'subscribed_fields': 'messages,messaging_postbacks,message_deliveries,message_reads',
            }, timeout=15).json()
        except requests.exceptions.RequestException as e:
            return {'ok': False, 'error': _('Could not reach Facebook: %s') % e}
        if 'error' in sub:
            return {'ok': False, 'error': sub['error'].get('message', 'Could not subscribe to Page webhook')}

        Channel = request.env['crm.channel'].sudo()
        channel = Channel.search([('meta_page_id', '=', page_id)], limit=1)
        vals = {
            'code': 'facebook',
            'name': page_name or page_id,
            'icon': 'fa-facebook',
            'meta_page_id': page_id,
            'page_access_token': page_access_token,
            'app_secret': app_secret,
            'verify_token': verify_token,
            'account_identifier': page_name,
        }
        if instagram_id:
            vals['meta_ig_account_id'] = instagram_id
        if channel:
            channel.write(vals)
        else:
            channel = Channel.create(vals)

        return {'ok': True, 'channel_id': channel.id, 'message': _('Page "%s" connected.') % (page_name or page_id)}
