# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class NelsisBondDemoLog(models.Model):
    _name = 'nelsis.bond.demo.log'
    _description = 'Bond Demo Data Load Log'
    _order = 'sequence, id'

    name = fields.Char(string='Step', required=True, index=True)
    sequence = fields.Integer(default=10)
    unit = fields.Char(string='Unit')
    state = fields.Selection(
        [('done', 'Loaded'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        required=True, default='done', index=True)
    message = fields.Text(string='Details')
    loaded_on = fields.Datetime(default=fields.Datetime.now)

    @api.model
    def _record(self, name, state, message=False, unit=False, sequence=None):
        rec = self.sudo().search([('name', '=', name)], limit=1)
        vals = {'state': state, 'message': (message or '')[-6000:] or False,
                'loaded_on': fields.Datetime.now()}
        if unit:
            vals['unit'] = unit
        if sequence is not None:
            vals['sequence'] = sequence
        if rec:
            rec.write(vals)
            return rec
        vals['name'] = name
        return self.sudo().create(vals)

    def action_rerun(self):
        """Run every step that is not loaded yet (failed steps are retried)."""
        from ..loader.runner import run_all
        failed = run_all(self.env)
        if failed:
            message = _('%s step(s) still failed. See the Load Log.', len(failed))
            kind = 'warning'
        else:
            message = _('All demo data steps are loaded.')
            kind = 'success'
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Bond demo data'), 'message': message,
                           'type': kind, 'sticky': False}}
