# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .constants import AMEND_STATES, G_MANAGER, G_OFFICER

AMEND_SUMMARY = 'LC amendment pending approval'


class NelsisLcAmendment(models.Model):
    _name = 'nelsis.lc.amendment'
    _description = 'LC Amendment'
    _inherit = ['nelsis.lc.guard.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'lc_id, sequence_no, id'

    name = fields.Char('Reference', readonly=True, copy=False, default='New', index=True)
    sequence_no = fields.Integer('Amendment No.', readonly=True, copy=False)
    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', required=True, index=True,
                            ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='lc_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='lc_id.currency_id', store=True)
    partner_id = fields.Many2one(related='lc_id.partner_id', store=True, string='Supplier')
    amendment_date = fields.Date(default=fields.Date.context_today, required=True)
    bank_reference = fields.Char('Bank Amendment Ref. / SWIFT')
    amount_change = fields.Monetary('Amount Change (+/-)', currency_field='currency_id', tracking=True)
    new_expiry_date = fields.Date('New Expiry Date', tracking=True)
    new_shipment_deadline = fields.Date('New Latest Shipment Date', tracking=True)
    reason = fields.Text(required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Pending Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='draft', required=True, readonly=True, copy=False, tracking=True, index=True)

    # Snapshots written at approval so history is never lost.
    prev_amount = fields.Monetary('Amount Before', currency_field='currency_id', readonly=True, copy=False)
    new_amount = fields.Monetary('Amount After', currency_field='currency_id', readonly=True, copy=False)
    prev_expiry_date = fields.Date('Expiry Before', readonly=True, copy=False)
    prev_shipment_deadline = fields.Date('Shipment Date Before', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved/Rejected By', readonly=True, copy=False)
    approved_on = fields.Datetime('Decision On', readonly=True, copy=False)
    reject_reason = fields.Text(readonly=True, copy=False)

    @api.constrains('amount_change', 'new_expiry_date', 'new_shipment_deadline')
    def _check_content(self):
        for rec in self:
            if not rec.amount_change and not rec.new_expiry_date and not rec.new_shipment_deadline:
                raise ValidationError(_('An amendment must change the amount, expiry date or shipment date.'))
            expiry = rec.new_expiry_date or rec.lc_id.expiry_date
            deadline = rec.new_shipment_deadline or rec.lc_id.shipment_deadline
            if rec.state in ('draft', 'submitted') and expiry and deadline and deadline > expiry:
                raise ValidationError(_('The latest shipment date cannot be after the expiry date.'))

    @api.model_create_multi
    def create(self, vals_list):
        next_no = {}
        for vals in vals_list:
            lc = self.env['nelsis.lc'].browse(vals.get('lc_id')).exists()
            if not lc:
                raise ValidationError(_('Select a Letter of Credit.'))
            if not self.env.su:
                if lc.state not in AMEND_STATES:
                    raise UserError(_('Amendments can only be raised for opened LC records.'))
                vals['state'] = 'draft'
            if lc.id not in next_no:
                last = self.search([('lc_id', '=', lc.id)], order='sequence_no desc', limit=1)
                next_no[lc.id] = last.sequence_no or 0
            next_no[lc.id] += 1
            vals['sequence_no'] = next_no[lc.id]
            vals['name'] = '%s/AMD-%02d' % (lc.name, next_no[lc.id])
        records = super().create(vals_list)
        for rec in records:
            rec.lc_id._log(_('Amendment %s created', rec.name))
        return records

    def write(self, vals):
        if not self.env.su:
            business = self._business_vals(vals)
            if business:
                if 'state' in business:
                    raise UserError(_('The status can only be changed through the workflow buttons.'))
                if business & {'lc_id', 'sequence_no', 'name'}:
                    raise UserError(_('The LC and numbering of an amendment cannot be changed.'))
                if any(rec.state != 'draft' for rec in self):
                    raise UserError(_('Submitted amendments are immutable. Reject it and raise a new one.'))
        return super().write(vals)

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_('Only draft amendments can be deleted.'))
        return super().unlink()

    # ---------------------------------------------------------------- workflow
    def _notify_managers(self):
        managers = self.env.ref(G_MANAGER).sudo().users.filtered(
            lambda u: u.active and not u.share)
        for rec in self:
            for user in managers:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=user.id, summary=AMEND_SUMMARY,
                    note=_('Amendment %(name)s of LC %(lc)s is waiting for approval.',
                           name=rec.name, lc=rec.lc_id.name))

    def _clear_alerts(self, feedback):
        for rec in self:
            rec.activity_ids.filtered(lambda a: a.summary == AMEND_SUMMARY).sudo().action_feedback(
                feedback=feedback)

    def action_submit(self):
        self._assert_group(G_OFFICER)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft amendments can be submitted.'))
            if rec.lc_id.state not in AMEND_STATES:
                raise UserError(_('LC %s is not open for amendments.', rec.lc_id.name))
        self.sudo().write({'state': 'submitted'})
        for rec in self:
            rec.lc_id._log(_('Amendment %s submitted for approval', rec.name))
        self._notify_managers()
        return True

    def action_approve(self):
        self._assert_group(G_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted amendments can be approved.'))
            lc = rec.lc_id
            if lc.state not in AMEND_STATES:
                raise UserError(_('LC %s is not open for amendments.', lc.name))
            if lc._setting().enforce_maker_checker and rec.create_uid == self.env.user:
                raise UserError(_('Company policy: the approver must be different from the creator.'))
            new_amount = lc.current_amount + rec.amount_change
            if new_amount <= 0:
                raise UserError(_('The amended LC amount must stay positive.'))
            limit = new_amount * (1 + lc.tolerance_percent / 100.0)
            if lc.currency_id.compare_amounts(lc.utilized_amount, limit) > 0:
                raise UserError(_('The amended amount (%(new)s) is below the amount already utilized (%(used)s).',
                                  new=new_amount, used=lc.utilized_amount))
            lc_vals = {
                'expiry_date': rec.new_expiry_date or lc.expiry_date,
                'shipment_deadline': rec.new_shipment_deadline or lc.shipment_deadline,
            }
            if rec.new_expiry_date and rec.new_expiry_date != lc.expiry_date:
                lc_vals['expiry_reminded'] = False
            if rec.new_shipment_deadline and rec.new_shipment_deadline != lc.shipment_deadline:
                lc_vals['deadline_reminded'] = False
            rec.sudo().write({
                'state': 'approved',
                'prev_amount': lc.current_amount,
                'new_amount': new_amount,
                'prev_expiry_date': lc.expiry_date,
                'prev_shipment_deadline': lc.shipment_deadline,
                'approved_by_id': self.env.uid,
                'approved_on': fields.Datetime.now(),
            })
            lc.sudo().write(lc_vals)
            lc._log(_('Amendment %s approved', rec.name), note=_(
                'Amount %(a)s -> %(b)s; expiry %(e1)s -> %(e2)s; latest shipment %(s1)s -> %(s2)s',
                a=rec.prev_amount, b=rec.new_amount, e1=rec.prev_expiry_date, e2=lc_vals['expiry_date'],
                s1=rec.prev_shipment_deadline, s2=lc_vals['shipment_deadline']))
        self._clear_alerts(_('Approved'))
        return True

    def action_reject(self):
        self._assert_group(G_MANAGER)
        self.ensure_one()
        return self._open_reason_wizard('amendment_reject', _('Reject Amendment'))

    def _do_reject(self, reason):
        self._assert_group(G_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted amendments can be rejected.'))
            rec.sudo().write({'state': 'rejected', 'reject_reason': reason,
                              'approved_by_id': self.env.uid, 'approved_on': fields.Datetime.now()})
            rec.lc_id._log(_('Amendment %s rejected', rec.name), note=reason)
        self._clear_alerts(_('Rejected'))
