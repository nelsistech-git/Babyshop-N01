# -*- coding: utf-8 -*-
import json
import logging
import random
import string

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

ACTION_TYPES = [
    ('edit', 'Edit'),
    ('delete', 'Delete'),
    ('discount', 'Discount Change'),
    ('price_change', 'Product Price Change'),
    ('stock_adjustment', 'Stock Adjustment'),
    ('sales_return', 'Sales Return / Refund'),
    ('expense', 'Expense Edit/Delete'),
    ('backdated', 'Backdated Transaction Change'),
    ('payment', 'Payment Edit/Delete'),
    ('customer_due', 'Customer Due Edit'),
    ('supplier_payment', 'Supplier Payment Edit'),
    ('purchase', 'Purchase Edit/Delete'),
]


class ExpressApprovalRequest(models.Model):
    _name = 'express.approval.request'
    _description = 'Express POS Approval Request'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(default=lambda self: _('New'), copy=False, readonly=True)
    res_model = fields.Char(required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    record_description = fields.Char(compute='_compute_record_description', store=True)

    action_type = fields.Selection(ACTION_TYPES, required=True, readonly=True)
    reason = fields.Text(required=True, readonly=True)
    old_values = fields.Text(readonly=True, help='JSON snapshot of the record before the change.')
    new_values = fields.Text(readonly=True, help='JSON snapshot of the requested change.')

    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    request_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    request_ip = fields.Char(readonly=True)
    request_device = fields.Char(readonly=True)

    requires_md_direct = fields.Boolean(
        readonly=True,
        help='High-risk changes (e.g. backdated transactions) require Managing Director scrutiny '
             'even while routing through the full chain.')

    state = fields.Selection([
        ('draft', 'Pending Manager'),
        ('manager_approved', 'Pending GM'),
        ('gm_approved', 'Pending MD'),
        ('approved', 'Approved & Applied'),
        ('rejected', 'Rejected'),
    ], default='draft', readonly=True, copy=False)

    manager_id = fields.Many2one('res.users', readonly=True, copy=False)
    manager_date = fields.Datetime(readonly=True, copy=False)
    gm_id = fields.Many2one('res.users', readonly=True, copy=False)
    gm_date = fields.Datetime(readonly=True, copy=False)
    md_id = fields.Many2one('res.users', readonly=True, copy=False)
    md_date = fields.Datetime(readonly=True, copy=False)

    log_ids = fields.One2many('express.approval.log', 'request_id', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)

    @api.depends('res_model', 'res_id')
    def _compute_record_description(self):
        for rec in self:
            desc = f'{rec.res_model} #{rec.res_id}'
            try:
                target = self.env[rec.res_model].browse(rec.res_id)
                if target.exists():
                    desc = target.display_name
            except Exception:
                pass
            rec.record_description = desc

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('express.approval.request') or _('New')
                vals['name'] = seq
        return super().create(vals_list)

    def _log(self, level, action, comment=False):
        self.ensure_one()
        self.env['express.approval.log'].create({
            'request_id': self.id,
            'level': level,
            'action': action,
            'comment': comment,
        })

    def _check_group(self, xmlid):
        if not self.env.user.has_group(xmlid):
            raise AccessError(_('You are not allowed to act on this approval step.'))

    def action_manager_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('This request is not pending Manager approval.'))
            rec._check_group('express_retail_pos.group_express_pos_branch_manager')
            rec.write({'state': 'manager_approved', 'manager_id': self.env.user.id, 'manager_date': fields.Datetime.now()})
            rec._log('manager', 'approve')

    def action_gm_approve(self):
        for rec in self:
            if rec.state != 'manager_approved':
                raise UserError(_('This request is not pending GM approval.'))
            rec._check_group('express_retail_pos.group_express_pos_gm')
            rec.write({'state': 'gm_approved', 'gm_id': self.env.user.id, 'gm_date': fields.Datetime.now()})
            rec._log('gm', 'approve')

    def action_md_approve(self):
        for rec in self:
            if rec.state not in ('gm_approved',):
                raise UserError(_('This request is not pending MD approval.'))
            rec._check_group('express_retail_pos.group_express_pos_md')
            rec.write({'state': 'approved', 'md_id': self.env.user.id, 'md_date': fields.Datetime.now()})
            rec._log('md', 'approve')
            rec._apply_change()

    def action_reject(self, comment=False):
        for rec in self:
            if rec.state in ('approved', 'rejected'):
                raise UserError(_('This request is already closed.'))
            level = {'draft': 'manager', 'manager_approved': 'gm', 'gm_approved': 'md'}.get(rec.state, 'manager')
            required_group = {
                'manager': 'express_retail_pos.group_express_pos_branch_manager',
                'gm': 'express_retail_pos.group_express_pos_gm',
                'md': 'express_retail_pos.group_express_pos_md',
            }[level]
            rec._check_group(required_group)
            rec.write({'state': 'rejected'})
            rec._log(level, 'reject', comment)

    def _apply_change(self):
        """Dispatch and apply the originally requested change now that full approval is granted.
        The write/unlink is executed with a bypass context flag so it does not re-trigger
        the approval guard on the target model.
        """
        self.ensure_one()
        model = self.env[self.res_model].sudo().browse(self.res_id)
        ctx = {'express_approval_bypass': True}
        new_values = json.loads(self.new_values) if self.new_values else {}

        if self.action_type == 'delete':
            if not model.exists():
                return
            if 'active' in model._fields:
                model.with_context(**ctx).write({'active': False})
            else:
                model.with_context(**ctx).unlink()
        elif self.action_type == 'sales_return':
            if model.exists():
                model.with_context(**ctx).action_express_return(new_values.get('return_lines', []))
        else:
            if model.exists() and new_values:
                model.with_context(**ctx).write(new_values)


class ExpressApprovalLog(models.Model):
    _name = 'express.approval.log'
    _description = 'Express POS Approval Audit Log Line'
    _order = 'date desc'

    request_id = fields.Many2one('express.approval.request', required=True, ondelete='cascade')
    level = fields.Selection([('manager', 'Manager'), ('gm', 'GM'), ('md', 'MD')])
    action = fields.Selection([('submit', 'Submitted'), ('approve', 'Approved'), ('reject', 'Rejected')], required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    comment = fields.Text()
    date = fields.Datetime(default=fields.Datetime.now, required=True)


class ExpressApprovalMixin(models.AbstractModel):
    """Inherit this mixin on any model whose edits/deletes must go through the
    Manager -> GM -> MD approval chain before being applied."""
    _name = 'express.approval.mixin'
    _description = 'Express Approval Mixin'

    def _express_request_ip_device(self):
        ip, device = False, False
        try:
            from odoo.http import request
            if request and request.httprequest:
                ip = request.httprequest.remote_addr
                device = request.httprequest.headers.get('User-Agent')
        except Exception:
            pass
        return ip, device

    def _express_create_approval(self, action_type, old_values, new_values, reason=False, requires_md_direct=False):
        self.ensure_one()
        ip, device = self._express_request_ip_device()
        request = self.env['express.approval.request'].sudo().create({
            'res_model': self._name,
            'res_id': self.id,
            'action_type': action_type,
            'old_values': json.dumps(old_values, default=str),
            'new_values': json.dumps(new_values, default=str),
            'reason': reason or _('No reason provided'),
            'requires_md_direct': requires_md_direct,
            'request_ip': ip,
            'request_device': device,
        })
        request._log(False, 'submit', reason)
        return request

    def _express_snapshot(self, fields_list):
        self.ensure_one()
        return {f: self[f] for f in fields_list if f in self._fields}
