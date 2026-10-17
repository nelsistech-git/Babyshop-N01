# -*- coding: utf-8 -*-
"""Shared state and helpers of the demo loader."""
import base64
import logging
import traceback
from datetime import timedelta

from odoo import Command, fields

from .pdf import make_pdf

_logger = logging.getLogger(__name__)

MODULE = 'nelsis_bond_demo'
PASSWORD = 'Demo@1234'
# Keep demo traffic quiet: no auto-subscription mails.
USER_CONTEXT = {
    'mail_create_nosubscribe': True,
    'mail_auto_subscribe_no_notify': True,
    'mail_notify_force_send': False,
}


class MissingDependency(Exception):
    pass


class Ctx(object):
    """Everything a loading unit needs: registry of created records, persona users,
    idempotent step runner and attachment helper."""

    def __init__(self, env):
        self.env = env
        self.today = fields.Date.today()
        self.company = env.company
        self.failed = []
        self.unit = ''
        self.seq = 0
        self._counter = 0

    # ------------------------------------------------------------------ dates
    def d(self, days=0):
        """Date relative to today."""
        return self.today + timedelta(days=days)

    # ----------------------------------------------------------- id registry
    def reg(self, key, record):
        """Remember a created record under a stable key (stored as external id)."""
        Data = self.env['ir.model.data'].sudo()
        data = Data.search([('module', '=', MODULE), ('name', '=', key)], limit=1)
        vals = {'model': record._name, 'res_id': record.id, 'noupdate': True}
        if data:
            data.write(vals)
        else:
            Data.create(dict(vals, module=MODULE, name=key))
        return record

    def get(self, key):
        """Record registered under ``key`` or None."""
        data = self.env['ir.model.data'].sudo().search(
            [('module', '=', MODULE), ('name', '=', key)], limit=1)
        if not data:
            return None
        return self.env[data.model].sudo().browse(data.res_id).exists() or None

    def need(self, key):
        record = self.get(key)
        if not record:
            raise MissingDependency('Required demo record "%s" was not loaded.' % key)
        return record

    # --------------------------------------------------------------- personas
    def user(self, persona):
        return self.need('user_' + persona)

    def u(self, record, persona):
        """``record`` re-bound to the persona user (real access rights apply)."""
        return record.with_user(self.user(persona)).with_context(**USER_CONTEXT)

    def model_as(self, persona, model_name):
        return self.u(self.env[model_name], persona)

    # ---------------------------------------------------------------- params
    def param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param('%s.%s' % (MODULE, key))

    def set_param(self, key, value='1'):
        self.env['ir.config_parameter'].sudo().set_param('%s.%s' % (MODULE, key), value)

    # ------------------------------------------------------------------ steps
    def step(self, key, func):
        """Run ``func`` once, inside a savepoint. Failures are logged, never raised."""
        Log = self.env['nelsis.bond.demo.log']
        self._counter += 1
        seq = self.seq + self._counter
        if self.param('step.' + key):
            return True
        try:
            with self.env.cr.savepoint():
                func()
        except Exception as exc:  # noqa - isolate every step
            _logger.warning('nelsis_bond_demo step %s failed: %s', key, exc)
            Log._record(key, 'failed', '%s: %s\n\n%s' % (type(exc).__name__, exc, traceback.format_exc()),
                        unit=self.unit, sequence=seq)
            self.failed.append(key)
            self.env.invalidate_all()
            return False
        self.set_param('step.' + key)
        Log._record(key, 'done', unit=self.unit, sequence=seq)
        return True

    # ------------------------------------------------------------ attachments
    def attach(self, record, name, title, lines=()):
        """Create a small fictitious PDF attached to ``record`` and return it."""
        self._counter += 1
        body = list(lines) + ['Ref: %s/%s/%s' % (record._name, record.id, name)]
        return self.env['ir.attachment'].sudo().create({
            'name': name if name.lower().endswith('.pdf') else name + '.pdf',
            'type': 'binary',
            'datas': base64.b64encode(make_pdf(title, body)),
            'mimetype': 'application/pdf',
            'res_model': record._name,
            'res_id': record.id,
        })

    @staticmethod
    def ids(*records):
        return Command.set([r.id for r in records])


def create_optional(model, vals, optional):
    """Create with the optional values; if that fails fall back to the mandatory ones."""
    try:
        with model.env.cr.savepoint():
            return model.create(dict(vals, **optional))
    except Exception as exc:  # noqa
        _logger.info('nelsis_bond_demo: optional values %s skipped (%s)', list(optional), exc)
        return model.create(vals)
