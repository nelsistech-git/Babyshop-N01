import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NelsisAnnouncement(models.Model):
    """Message written by an administrator in Odoo and delivered to the employees' phones.

    * Push: sent through Firebase Cloud Messaging when FCM is configured in Settings.
    * Always: shown in the app (bell icon / Announcements list) and, when push is not configured, the app picks
      new announcements up within about a minute and shows a phone notification itself.
    """
    _name = 'nelsis.announcement'
    _description = 'Mobile App Announcement'
    _order = 'sent_date desc, id desc'

    name = fields.Char(string='Title', required=True)
    body = fields.Text(string='Message', required=True,
                       help='This text is shown in the phone notification and in the app.')
    audience = fields.Selection([('all', 'All employees'), ('department', 'Departments'), ('employee', 'Selected employees')],
                                default='all', required=True)
    department_ids = fields.Many2many('hr.department', 'nelsis_announcement_dept_rel', 'announcement_id', 'department_id',
                                      string='Departments')
    employee_ids = fields.Many2many('hr.employee', 'nelsis_announcement_emp_rel', 'announcement_id', 'employee_id',
                                    string='Employees')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    expire_date = fields.Datetime(string='Hide after', help='Empty = keep showing in the app.')
    state = fields.Selection([('draft', 'Draft'), ('sent', 'Sent')], default='draft', required=True, copy=False)
    sent_date = fields.Datetime(copy=False, readonly=True)
    sent_by_id = fields.Many2one('res.users', copy=False, readonly=True)
    push_state = fields.Selection([('none', 'Not sent'), ('queued', 'Queued'), ('done', 'Delivered to push service'),
                                   ('partial', 'Partly delivered'), ('failed', 'Failed'),
                                   ('skipped', 'Push not configured')], default='none', copy=False, readonly=True)
    push_total = fields.Integer(string='Devices', copy=False, readonly=True)
    push_ok = fields.Integer(string='Accepted', copy=False, readonly=True)
    push_error = fields.Text(copy=False, readonly=True)
    recipient_count = fields.Integer(compute='_compute_recipient_count')

    @api.depends('audience', 'department_ids', 'employee_ids', 'company_id')
    def _compute_recipient_count(self):
        for rec in self:
            rec.recipient_count = len(rec._target_employees())

    # ------------------------------------------------------------------ audience
    def _target_employees(self):
        self.ensure_one()
        dom = [('user_id', '!=', False)]
        if self.company_id:
            dom.append(('company_id', '=', self.company_id.id))
        if self.audience == 'department':
            dom.append(('department_id', 'in', self.department_ids.ids))
        elif self.audience == 'employee':
            dom.append(('id', 'in', self.employee_ids.ids))
        return self.env['hr.employee'].sudo().search(dom)

    @api.model
    def visible_domain(self, employee):
        """Announcements this employee may see in the app."""
        return [
            ('state', '=', 'sent'),
            ('company_id', 'in', [False, employee.company_id.id]),
            '|', ('expire_date', '=', False), ('expire_date', '>', fields.Datetime.now()),
            '|', '|', ('audience', '=', 'all'),
            '&', ('audience', '=', 'department'), ('department_ids', 'in', employee.department_id.ids),
            '&', ('audience', '=', 'employee'), ('employee_ids', 'in', employee.ids),
        ]

    # ------------------------------------------------------------------ sending
    def action_send(self):
        for rec in self:
            if rec.state == 'sent':
                continue
            if not (rec.name or '').strip() or not (rec.body or '').strip():
                raise UserError(_('Please write a title and a message.'))
            if rec.audience == 'department' and not rec.department_ids:
                raise UserError(_('Choose at least one department.'))
            if rec.audience == 'employee' and not rec.employee_ids:
                raise UserError(_('Choose at least one employee.'))
            rec.write({'state': 'sent', 'sent_date': fields.Datetime.now(), 'sent_by_id': self.env.user.id,
                       'push_state': 'queued'})
        cron = self.env.ref('nelsis_field_tracking.cron_nelsis_announcement_push', raise_if_not_found=False)
        if cron:
            try:
                cron.sudo()._trigger()   # run the push job right away instead of waiting for the next minute
            except Exception:  # noqa: BLE001
                pass
        return True

    def action_resend_push(self):
        """Send the phone notification again (e.g. after fixing the Firebase settings)."""
        self.filtered(lambda r: r.state == 'sent').write({'push_state': 'queued'})
        return True

    def _push(self):
        self.ensure_one()
        Fcm = self.env['nelsis.fcm'].sudo()
        if not Fcm.configured():
            self.write({'push_state': 'skipped', 'push_total': 0, 'push_ok': 0,
                        'push_error': _('Firebase is not set up in Field Force > Settings. Employees still see the '
                                        'announcement inside the app and get a phone notification within about a minute '
                                        'while the app is running.')})
            return
        users = self._target_employees().user_id
        now = fields.Datetime.now()
        tokens = self.env['nelsis.api.token'].sudo().search([
            ('user_id', 'in', users.ids), ('revoked', '=', False), ('fcm_token', '!=', False), ('expires_at', '>', now)])
        seen, ok, errors = set(), 0, []
        data = {'type': 'announcement', 'announcement_id': str(self.id)}
        for tok in tokens:
            if tok.fcm_token in seen:
                continue
            seen.add(tok.fcm_token)
            result = Fcm.send(tok.fcm_token, self.name, self.body, data)
            if result == 'ok':
                ok += 1
            elif result == 'invalid':
                tok.fcm_token = False          # phone uninstalled the app / token rotated
            else:
                errors.append(result)
        total = len(seen)
        state = 'done' if ok == total else ('partial' if ok else 'failed')
        if total == 0:
            state = 'done'
        self.write({'push_state': state, 'push_total': total, 'push_ok': ok,
                    'push_error': '\n'.join(sorted(set(errors))[:5]) or False})

    @api.model
    def _cron_push_pending(self):
        for rec in self.sudo().search([('push_state', '=', 'queued')], limit=20):
            try:
                rec._push()
                self.env.cr.commit()
            except Exception as e:  # noqa: BLE001
                self.env.cr.rollback()
                _logger.exception('Announcement push failed')
                rec.write({'push_state': 'failed', 'push_error': str(e)[:500]})
                self.env.cr.commit()
