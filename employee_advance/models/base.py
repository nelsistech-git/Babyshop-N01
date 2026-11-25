from markupsafe import escape

from odoo import api, Command, fields, models, _
from odoo.exceptions import AccessError, UserError

G_SUPERVISOR = 'employee_advance.group_advance_manager'
G_ACCOUNTANT = 'employee_advance.group_advance_accountant'


class EmployeeAdvanceBase(models.AbstractModel):
    """Shared helpers for the advance and the adjustment documents."""
    _name = 'employee.advance.base'
    _description = 'Employee Advance Helpers'

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1)

    @api.model
    def _account_by_code(self, code):
        return self.env['account.account'].search(
            [('code', '=', code), ('company_id', '=', self.env.company.id)], limit=1)

    def _check_group(self, xmlid):
        if not self.env.user.has_group(xmlid):
            raise AccessError(_('You are not allowed to perform this action.'))

    def _check_state(self, *states):
        for rec in self:
            if rec.state not in states:
                raise UserError(_('%(name)s: invalid state for this action.', name=rec.name))

    def _get_partner(self):
        self.ensure_one()
        partner = self.employee_id.work_contact_id
        if not partner:
            raise UserError(_('Employee %s has no work contact.', self.employee_id.name))
        return partner

    def _ensure_reconcile(self, account):
        """The advance head must allow reconciliation; switch it on if needed."""
        if not account.reconcile:
            account.sudo().write({'reconcile': True})
            self.message_post(body=escape(
                _('Account %s was set to Allow Reconciliation.', account.display_name)))

    def _line(self, name, account, partner, debit=0.0, credit=0.0):
        return Command.create({
            'name': name,
            'account_id': account.id,
            'partner_id': partner.id,
            'debit': debit,
            'credit': credit,
        })

    def _create_move(self, lines):
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_('No Miscellaneous Operations journal found.'))
        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'company_id': self.company_id.id,
            'line_ids': lines,
        })
        move.action_post()
        return move

    def _reconcile(self, moves, account):
        lines = moves.sudo().line_ids.filtered(
            lambda l: l.account_id == account and not l.reconciled)
        lines.reconcile()
