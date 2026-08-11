# -*- coding: utf-8 -*-
import uuid
import json
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools
_logger = logging.getLogger(__name__)


class ChatWorkQueue(models.Model):
    _name = 'acrux.chat.work.queue'
    _description = 'Work Queue'
    _rec_name = 'ttype'
    _order = 'id'

    name = fields.Char('Name Unique', default=lambda s: str(uuid.uuid1()), required=True,
                       readonly=True, copy=False)
    data = fields.Text('Data')
    trace_log = fields.Text('Log')
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', required=True,
                                   ondelete='cascade')
    res_id = fields.Integer('Resource ID for model')
    ttype = fields.Selection([('delete_me', 'To Delete'),
                              ('error', 'Error'),
                              ('in_message', 'IN Message'),
                              ('in_event', 'IN Event'),
                              ('in_update', 'IN Update')],
                             string='Type', required=True)

    _sql_constraints = [
        ('work_name_uniq', 'unique (name)', 'Key must be unique.')
    ]

    @api.autovacuum
    def _gc_delete_me(self):
        self.sudo().search([('ttype', '=', 'delete_me')]).unlink()
        self.search([('write_date', '<', datetime.now() + relativedelta(weeks=-1))]).unlink()

    @api.model
    def queue_trigger(self, delay=0):
        '''
        Si cron inactivo, no ejecuta si fecha menor a now.
        Se puede pasar fecha como param a _trigger()
        '''
        cron_id = self.env.ref('whatsapp_connector.whatsapp_connector_work_queue')
        datetime = fields.Datetime.now()
        if delay:
            datetime += relativedelta(seconds=delay)
        cron_id._trigger(datetime)

    @api.model
    def _cron_process_queue(self, run_trigger=False):
        ''' call only from cron, please '''
        records = self.search([('ttype', 'not in', ['delete_me', 'error'])], limit=500)
        records.process_record()
        if run_trigger or len(records) == 500:
            self.queue_trigger()

    def process_record(self, with_commit=True):
        in_message_ids = self.env['acrux.chat.message'].sudo()
        records = self.filtered(lambda r: r.ttype in ['in_message', 'in_event', 'in_update'])
        for connector_id, recs in tools.groupby(records, lambda msg: msg.connector_id):
            ctx = {
                'tz': connector_id.tz,
                'lang': connector_id.company_id.partner_id.lang,
                'allowed_company_ids': [connector_id.company_id.id],
                'from_webhook': True
            }
            connector_id = connector_id.with_context(ctx)
            Conversation = self.env['acrux.chat.conversation'].sudo().with_context(ctx)
            for rec in recs:
                try:
                    data = json.loads(rec.data)

                    if rec.ttype == 'in_message':
                        data = Conversation.parse_message_receive(connector_id, data)
                        message_id = Conversation.new_message(data)
                        in_message_ids += message_id

                    elif rec.ttype == 'in_event':
                        event = Conversation.parse_event_receive(connector_id, data)
                        Conversation.new_webhook_event(connector_id, event)

                    elif rec.ttype == 'in_update':
                        contact = Conversation.parse_contact_receive(connector_id, data)
                        Conversation.contact_update(connector_id, contact)

                except Exception as e:
                    self.env.cr.rollback()
                    rec.ttype = 'error'
                    rec.trace_log = tools.ustr(e)
                    _logger.error('Error', exc_info=True)
                else:
                    rec.ttype = 'delete_me'
                finally:
                    ''' Caution:
                        Without commit previous records are not saved if error '''
                    if with_commit:
                        self.env.cr.commit()
        return {'in_message': in_message_ids}
