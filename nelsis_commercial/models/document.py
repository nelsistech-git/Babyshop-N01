# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from .constants import G_USER, G_OFFICER, G_MANAGER, require_group

PROTECTED_FIELDS = {'document_type_id', 'number', 'issue_date', 'expiry_date', 'attachment_ids',
                    'file_id', 'issuing_org'}


class NelsisCommercialDocument(models.Model):
    _name = 'nelsis.commercial.document'
    _description = 'Commercial Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'file_id, document_type_id, version desc'

    file_id = fields.Many2one('nelsis.commercial.file', string='Commercial File', required=True,
                              ondelete='restrict', index=True, tracking=True)
    company_id = fields.Many2one(related='file_id.company_id', store=True, index=True)
    lc_display = fields.Char(related='file_id.lc_display', string='LC')
    shipment_id = fields.Many2one('nelsis.commercial.shipment', domain="[('file_id', '=', file_id)]")
    document_type_id = fields.Many2one('nelsis.commercial.document.type', required=True, tracking=True)
    number = fields.Char(string='Document Number', required=True, tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    issuing_org = fields.Char(string='Issuing Organization')
    version = fields.Integer(default=1, readonly=True, copy=False)
    previous_id = fields.Many2one('nelsis.commercial.document', string='Previous Version', readonly=True, copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('verified', 'Verified'),
         ('rejected', 'Rejected'), ('superseded', 'Superseded')],
        default='draft', required=True, tracking=True, copy=False)
    is_expired = fields.Boolean(compute='_compute_is_expired')
    attachment_ids = fields.Many2many('ir.attachment', 'nelsis_commercial_document_attachment_rel',
                                      'document_id', 'attachment_id', string='Attachments', copy=False)
    verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    verified_date = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Text(copy=False)
    remarks = fields.Text()

    # ------------------------------------------------------------------ computes
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.expiry_date and rec.expiry_date < today)

    @api.depends('document_type_id.name', 'number', 'version')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = ('%s %s (v%s)' % (rec.document_type_id.name or '', rec.number or '', rec.version)).strip()

    # ------------------------------------------------------------------ constraints
    @api.constrains('expiry_date', 'issue_date')
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.expiry_date and rec.expiry_date < rec.issue_date:
                raise ValidationError(_("Expiry date cannot be earlier than issue date."))

    @api.constrains('document_type_id', 'number', 'state')
    def _check_unique_number(self):
        for rec in self:
            if rec.state == 'superseded':
                continue
            dup = self.sudo().search_count([
                ('id', '!=', rec.id), ('document_type_id', '=', rec.document_type_id.id),
                ('number', '=', rec.number), ('company_id', '=', rec.company_id.id),
                ('state', '!=', 'superseded')])
            if dup:
                raise ValidationError(_("Document %(type)s number %(num)s already exists. Create a new version instead of a duplicate.",
                                        type=rec.document_type_id.name, num=rec.number))

    @api.constrains('attachment_ids')
    def _check_attachments(self):
        setting = self.env['nelsis.commercial.setting'].get_setting()
        allowed = {e.strip().lower() for e in (setting.allowed_extensions or '').split(',') if e.strip()}
        max_bytes = int((setting.max_file_size_mb or 0) * 1024 * 1024)
        for rec in self:
            for att in rec.attachment_ids:
                fname = att.name or ''
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if allowed and ext not in allowed:
                    raise ValidationError(_("File type '.%(ext)s' is not allowed (%(name)s).", ext=ext, name=fname))
                if max_bytes and (att.file_size or 0) > max_bytes:
                    raise ValidationError(_("File %(name)s exceeds the allowed size of %(mb)s MB.",
                                            name=fname, mb=setting.max_file_size_mb))
                if att.checksum:
                    dup = self.sudo().search_count([
                        ('id', '!=', rec.id), ('state', '!=', 'superseded'),
                        ('attachment_ids.checksum', '=', att.checksum)])
                    if dup:
                        raise ValidationError(_("The file %s was already uploaded to another commercial document.", fname))

    # ------------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('state', None)
        records = super().create(vals_list)
        records._link_attachments()
        return records

    def write(self, vals):
        if 'state' in vals:
            target = vals['state']
            if target in ('verified', 'rejected'):
                require_group(self.env, G_MANAGER)
            elif target in ('draft', 'superseded'):
                require_group(self.env, G_OFFICER)
            else:
                require_group(self.env, G_USER)
        if PROTECTED_FIELDS & set(vals):
            if self.filtered(lambda d: d.state in ('verified', 'superseded')):
                raise UserError(_("Verified or superseded documents are locked. Create a new version instead."))
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments()
        return res

    def unlink(self):
        if any(rec.state != 'draft' or rec.version > 1 for rec in self):
            raise UserError(_("Only first-version draft documents can be deleted; others are kept for audit history."))
        return super().unlink()

    def _link_attachments(self):
        """Bind attachments to this record so Odoo's own access checks follow this model's ACLs."""
        for rec in self:
            atts = rec.attachment_ids.filtered(lambda a: a.res_model != rec._name or a.res_id != rec.id)
            if atts:
                atts.sudo().write({'res_model': rec._name, 'res_id': rec.id})

    # ------------------------------------------------------------------ workflow
    def action_submit(self):
        require_group(self.env, G_USER)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft documents can be submitted."))
            if not rec.attachment_ids:
                raise UserError(_("Attach the document file before submitting."))
        self.write({'state': 'submitted'})

    def action_verify(self):
        require_group(self.env, G_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted documents can be verified."))
            if not rec.attachment_ids:
                raise UserError(_("A document without an attachment cannot be verified."))
            if rec.is_expired:
                raise UserError(_("An expired document cannot be verified."))
        self.write({'state': 'verified', 'verified_by': self.env.user.id, 'verified_date': fields.Datetime.now()})

    def action_reject(self):
        require_group(self.env, G_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted documents can be rejected."))
            if not rec.rejection_reason:
                raise UserError(_("Enter a rejection reason first."))
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        require_group(self.env, G_OFFICER)
        for rec in self:
            if rec.state != 'rejected':
                raise UserError(_("Only rejected documents can be reset to draft."))
        self.write({'state': 'draft'})

    def action_new_version(self):
        require_group(self.env, G_OFFICER)
        self.ensure_one()
        if self.state not in ('verified', 'rejected', 'submitted'):
            raise UserError(_("A new version can be created from a verified, submitted or rejected document."))
        old = self
        old.write({'state': 'superseded'})
        new = self.create({
            'file_id': old.file_id.id, 'shipment_id': old.shipment_id.id,
            'document_type_id': old.document_type_id.id, 'number': old.number,
            'issue_date': old.issue_date, 'expiry_date': old.expiry_date,
            'issuing_org': old.issuing_org, 'version': old.version + 1, 'previous_id': old.id,
            'remarks': old.remarks,
        })
        old.message_post(body=_("Superseded by version %s.", new.version))
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': new.id,
                'view_mode': 'form', 'target': 'current'}

    # ------------------------------------------------------------------ cron
    @api.model
    def _cron_check_expiry(self):
        today = fields.Date.context_today(self)
        docs = self.search([('state', '=', 'verified'), ('expiry_date', '<', today),
                            ('file_id.state', 'not in', ('done', 'cancel', 'rejected'))])
        for doc in docs:
            summary = _("Expired document: %s", doc.display_name)
            fobj = doc.file_id
            if not fobj.activity_ids.filtered(lambda a: a.summary == summary):
                fobj.activity_schedule('mail.mail_activity_data_todo', summary=summary,
                                       user_id=(fobj.user_id or self.env.user).id)
