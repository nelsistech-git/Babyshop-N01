# -*- coding: utf-8 -*-
from odoo import api, models


class CrmOmniChatContext(models.AbstractModel):
    _name = 'crm.omni.chat.context'
    _description = 'Chat Room Contextual Panel Data Provider'

    def _model_exists(self, model_name):
        return model_name in self.env.registry.models

    @api.model
    def get_partner_context(self, partner_id):
        """Aggregate everything the Chat Room's right-hand info panel needs
        for one customer, in a single round trip. Sales / Invoicing / Stock
        sections degrade gracefully (available: False) if those apps
        aren't installed, rather than raising."""
        partner = self.env['res.partner'].sudo().browse(partner_id)
        if not partner.exists():
            return {}

        data = {
            'contact': {
                'id': partner.id,
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone or partner.mobile,
                'city': partner.city,
                'country': partner.country_id.name if partner.country_id else False,
                'is_company': partner.is_company,
                'is_customer': partner.customer_rank > 0,
                'is_vendor': partner.supplier_rank > 0,
            },
            'lead': False,
            'sales': {'available': False, 'orders': []},
            'invoices': {'available': False, 'items': []},
            'deliveries': {'available': False, 'items': []},
            'history': [],
        }

        lead = self.env['crm.lead'].sudo().search([
            ('partner_id', '=', partner.id), ('active', '=', True)],
            limit=1, order='create_date desc')
        if lead:
            data['lead'] = {
                'id': lead.id,
                'name': lead.name,
                'stage': lead.stage_id.name if lead.stage_id else False,
                'expected_revenue': lead.expected_revenue,
                'probability': round(lead.probability or 0.0, 1),
                'source': lead.source_id.name if lead.source_id else False,
                'type': lead.type,
            }

        if self._model_exists('sale.order'):
            try:
                orders = self.env['sale.order'].sudo().search(
                    [('partner_id', '=', partner.id)], limit=10, order='date_order desc')
                data['sales'] = {
                    'available': True,
                    'orders': [{
                        'id': o.id, 'name': o.name, 'amount_total': o.amount_total,
                        'state': o.state, 'date_order': o.date_order,
                    } for o in orders],
                }
            except Exception:
                pass

        if self._model_exists('account.move'):
            try:
                invoices = self.env['account.move'].sudo().search([
                    ('partner_id', '=', partner.id), ('move_type', '=', 'out_invoice')],
                    limit=10, order='invoice_date desc')
                data['invoices'] = {
                    'available': True,
                    'items': [{
                        'id': i.id, 'name': i.name, 'amount_total': i.amount_total,
                        'payment_state': i.payment_state, 'invoice_date': i.invoice_date,
                    } for i in invoices],
                }
            except Exception:
                pass

        if self._model_exists('stock.picking'):
            try:
                pickings = self.env['stock.picking'].sudo().search(
                    [('partner_id', '=', partner.id)], limit=10, order='scheduled_date desc')
                data['deliveries'] = {
                    'available': True,
                    'items': [{
                        'id': p.id, 'name': p.name, 'state': p.state,
                        'scheduled_date': p.scheduled_date,
                    } for p in pickings],
                }
            except Exception:
                pass

        comms = self.env['crm.communication'].sudo().search(
            [('partner_id', '=', partner.id)], limit=30, order='date desc')
        data['history'] = [{
            'id': c.id, 'subject': c.subject, 'comm_type': c.comm_type,
            'date': c.date, 'channel': c.channel_id.name if c.channel_id else False,
            'agent': c.agent_id.name if c.agent_id else False,
        } for c in comms]

        return data
