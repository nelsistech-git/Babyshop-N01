# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPortalMessage(models.Model):
    """Buyer-Merchant Portal Message (SRS sections 13, 16) — garment.portal.message.

    Implements the Buyer Comment Management workflow: Buyer Comment ->
    Assigned Team -> Action Taken -> Response Submitted -> Buyer Confirmation,
    plus the Communication Center's message thread / file sharing / mention.
    """
    _name = 'garment.portal.message'
    _description = 'Buyer Portal Message'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Ref.', copy=False, readonly=True, default=lambda s: _('New'))

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='From (Buyer Contact)', tracking=True,
                                  help='Left empty when the message was posted by an internal factory user.')
    author_user_id = fields.Many2one('res.users', string='From (Internal User)', tracking=True)
    direction = fields.Selection([
        ('inbound', 'Buyer -> Factory'), ('outbound', 'Factory -> Buyer'),
    ], string='Direction', required=True, default='inbound', tracking=True)

    order_id = fields.Many2one('garment.order', string='Related Order')
    sample_id = fields.Many2one('garment.sample', string='Related Sample')
    techpack_id = fields.Many2one('garment.techpack', string='Related Tech Pack')
    shipment_id = fields.Many2one('garment.shipment', string='Related Shipment')

    parent_id = fields.Many2one('garment.portal.message', string='In Reply To', ondelete='cascade', index=True)
    reply_ids = fields.One2many('garment.portal.message', 'parent_id', string='Replies')
    reply_count = fields.Integer(string='Replies', compute='_compute_reply_count')

    mentioned_partner_ids = fields.Many2many('res.partner', string='Mentioned Users')

    subject = fields.Char(string='Subject')
    body = fields.Html(string='Message', sanitize=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    responsible_department = fields.Selection([
        ('merchandising', 'Merchandising'), ('quality', 'Quality'), ('production', 'Production'),
        ('logistics', 'Logistics'), ('commercial', 'Commercial'), ('sampling', 'Sampling'),
    ], string='Responsible Department', tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)

    completion_status = fields.Selection([
        ('open', 'Buyer Comment'),
        ('assigned', 'Assigned Team'),
        ('action_taken', 'Action Taken'),
        ('response_submitted', 'Response Submitted'),
        ('confirmed', 'Buyer Confirmation'),
    ], string='Completion Status', default='open', tracking=True, group_expand='_expand_states')

    message_date = fields.Datetime(string='Message Date', default=fields.Datetime.now)
    is_read = fields.Boolean(string='Read by Buyer', default=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['completion_status'].selection]

    @api.depends('reply_ids')
    def _compute_reply_count(self):
        for rec in self:
            rec.reply_count = len(rec.reply_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.portal.message') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow (SRS section 13)
    # ------------------------------------------------------------------
    def action_assign(self, department=None):
        self.write({'completion_status': 'assigned', 'responsible_department': department or self.responsible_department})

    def action_mark_action_taken(self):
        self.write({'completion_status': 'action_taken'})

    def action_submit_response(self, body, author_user=None):
        self.ensure_one()
        reply = self.create({
            'buyer_id': self.buyer_id.id, 'parent_id': self.id, 'direction': 'outbound',
            'subject': _('Re: %s') % (self.subject or self.name),
            'body': body, 'author_user_id': (author_user or self.env.user).id,
            'order_id': self.order_id.id, 'sample_id': self.sample_id.id,
            'techpack_id': self.techpack_id.id, 'shipment_id': self.shipment_id.id,
            'responsible_department': self.responsible_department,
            'completion_status': 'response_submitted',
        })
        self.write({'completion_status': 'response_submitted'})
        return reply

    def action_buyer_confirm(self):
        self.write({'completion_status': 'confirmed', 'is_read': True})
