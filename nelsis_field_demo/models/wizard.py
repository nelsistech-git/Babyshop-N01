from odoo import api, fields, models, _
from odoo.exceptions import AccessError

from . import sim
from .generator import PASSWORD

MODEL_LABELS = [
    ('res.users', 'Users'), ('hr.employee', 'Employees'), ('nelsis.work.site', 'Work sites'),
    ('hr.attendance', 'Attendances'), ('nelsis.location.log', 'GPS points'),
    ('nelsis.presence.log', 'Online/offline events'), ('nelsis.announcement', 'Announcements'),
    ('nelsis.api.token', 'App devices'), ('conveyance.sheet', 'TA/DA claims'),
    ('employee.advance', 'Advances'), ('nelsis.ai.insight', 'AI insights'),
]


class NelsisDemoWizard(models.TransientModel):
    _name = 'nelsis.demo.wizard'
    _description = 'Nelsis demo data'

    demo_exists = fields.Boolean(compute='_compute_info')
    summary = fields.Text(string='What is in the database now', compute='_compute_info')
    accounts = fields.Text(string='Demo sign-in accounts', compute='_compute_info')
    result = fields.Text(string='Last run', readonly=True)

    @api.depends_context('uid')
    def _compute_info(self):
        gen = self.env['nelsis.demo.generator']
        counts = gen.counts()
        for w in self:
            w.demo_exists = bool(counts)
            if counts:
                w.summary = '\n'.join('%-26s %s' % (label, counts[m]) for m, label in MODEL_LABELS if counts.get(m))
                w.accounts = 'Password for all: %s\n%s' % (PASSWORD, '\n'.join(
                    '%-14s %-18s %s' % (e[0], e[1], 'Administrator (map & analysis)' if e[0] == sim.MANAGER_LOGIN
                                        else ('field staff' if e[4] else 'office staff'))
                    for e in sim.EMPLOYEES))
            else:
                w.summary = _('No demo data yet.')
                w.accounts = False

    def _check(self):
        if not self.env.user.has_group('nelsis_field_tracking.group_nelsis_manager'):
            raise AccessError(_('Only Field Force administrators can manage demo data.'))

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'new', 'name': _('Demo data')}

    def action_generate(self):
        self._check()
        gen = self.env['nelsis.demo.generator'].sudo()
        removed, failed = gen.remove_all()
        notes = gen.generate()
        lines = []
        if removed:
            lines.append('Old demo data removed: %d records.' % removed)
        lines += ['Could not remove: %s' % f for f in failed]
        self.result = '\n'.join(lines + notes)
        return self._reopen()

    def action_remove(self):
        self._check()
        removed, failed = self.env['nelsis.demo.generator'].sudo().remove_all()
        self.result = 'Removed %d demo records.%s' % (removed, ('\nCould not remove: ' + '; '.join(failed)) if failed else '')
        return self._reopen()
