# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentPortalAccessRequest(models.Model):
    """Buyer Portal Access Request (SRS sections 21-22) — garment.portal.access.request.

    Covers Buyer Registration & Approval: a request can be for a brand-new
    buyer (no `buyer_id` set) or for an additional portal user of an
    existing buyer (SRS section 7 - "a buyer can have multiple users").
    Approval creates/links the `garment.buyer`, a `garment.buyer.contact`
    and a real Odoo portal user (via the standard `portal.wizard`), then
    sends the welcome email.
    """
    _name = 'garment.portal.access.request'
    _description = 'Buyer Portal Access Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Request No.', copy=False, readonly=True, default=lambda s: _('New'))

    source = fields.Selection([
        ('crm_lead', 'CRM Lead Conversion'),
        ('manual', 'Manual Creation'),
        ('invitation_link', 'Invitation Link'),
        ('api', 'API Integration'),
    ], string='Registration Source', default='manual', required=True, tracking=True)

    buyer_id = fields.Many2one('garment.buyer', string='Existing Buyer', tracking=True,
                                help='Set when requesting an additional portal user for an existing buyer. '
                                     'Leave empty for a brand-new buyer registration.')

    # ------------------------------------------------------------------
    # Registration Information (SRS section 22)
    # ------------------------------------------------------------------
    company_name = fields.Char(string='Company Name', required=True, tracking=True)
    brand_name = fields.Char(string='Brand Name')
    country_id = fields.Many2one('res.country', string='Country')
    website = fields.Char(string='Website')
    business_category = fields.Char(string='Business Category')
    buyer_type = fields.Selection([
        ('domestic', 'Domestic'), ('export', 'Export'), ('international', 'International'),
    ], string='Buyer Type', default='international')

    contact_person = fields.Char(string='Contact Person', required=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone')

    requested_role = fields.Selection([
        ('buyer_admin', 'Buyer Admin - Full Buyer Access'),
        ('buyer_merchandiser', 'Buyer Merchandiser - Order & Sample'),
        ('buyer_qa', 'Buyer QA - Quality Data'),
        ('buyer_logistics', 'Buyer Logistics - Shipment Data'),
    ], string='Requested Portal Role', default='buyer_merchandiser', required=True, tracking=True)
    department = fields.Char(string='Department')

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)

    # ------------------------------------------------------------------
    # Approval Workflow (SRS section 22)
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Registration Request'),
        ('sales_review', 'Sales Review'),
        ('management_approval', 'Management Approval'),
        ('approved', 'Portal Account Created'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)
    review_date = fields.Datetime(string='Review Date', readonly=True, copy=False)
    rejection_reason = fields.Text(string='Rejection Reason')

    partner_id = fields.Many2one('res.partner', string='Portal Contact Created', readonly=True, copy=False)
    welcome_email_sent = fields.Boolean(string='Welcome Email Sent', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['state'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.portal.access.request') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_start_sales_review(self):
        self.write({'state': 'sales_review'})

    def action_send_for_management_approval(self):
        self.write({'state': 'management_approval'})

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                raise UserError(_('Please record a Rejection Reason before rejecting request "%s".') % rec.name)
        self.write({
            'state': 'rejected', 'reviewed_by_id': self.env.user.id, 'review_date': fields.Datetime.now(),
        })

    def action_approve(self):
        """Portal Account Created -> Welcome Email Sent (SRS section 22)."""
        for rec in self:
            buyer = rec._get_or_create_buyer()
            partner = rec._get_or_create_portal_partner(buyer)
            rec._grant_portal_access(partner)
            rec.write({
                'state': 'approved', 'buyer_id': buyer.id, 'partner_id': partner.id,
                'reviewed_by_id': self.env.user.id, 'review_date': fields.Datetime.now(),
                'welcome_email_sent': True,
            })
            self.env['garment.portal.activity.log'].sudo().create({
                'partner_id': partner.id, 'buyer_id': buyer.id, 'activity_type': 'account_approved',
                'description': _('Portal access request %s approved for %s; welcome email sent.') % (
                    rec.name, partner.name),
            })
            rec.message_post(body=_('Buyer Portal account created and welcome email sent to %s.') % rec.email)

    def _get_or_create_buyer(self):
        self.ensure_one()
        if self.buyer_id:
            return self.buyer_id
        buyer = self.env['garment.buyer'].create({
            'name': self.company_name,
            'brand_name': self.brand_name,
            'country_id': self.country_id.id,
            'website': self.website,
            'buyer_type': self.buyer_type,
            'email': self.email,
            'phone': self.phone,
        })
        buyer.action_create_related_partner()
        return buyer

    def _get_or_create_portal_partner(self, buyer):
        self.ensure_one()
        Partner = self.env['res.partner']
        partner = Partner.search([('email', '=', self.email), ('garment_buyer_id', '=', buyer.id)], limit=1)
        if not partner:
            if not buyer.partner_id:
                buyer.action_create_related_partner()
            if self.requested_role == 'buyer_admin' and not buyer.partner_id.email:
                # First / admin user: use the buyer's own company partner as the login.
                partner = buyer.partner_id
                partner.write({'name': self.contact_person or partner.name, 'email': self.email,
                                'phone': self.phone})
            else:
                partner = Partner.create({
                    'name': self.contact_person,
                    'email': self.email,
                    'phone': self.phone,
                    'parent_id': buyer.partner_id.id if buyer.partner_id else False,
                    'company_name': buyer.name,
                })
        partner.write({
            'garment_buyer_id': buyer.id,
            'garment_portal_role': self.requested_role,
            'garment_portal_department': self.department,
        })
        if not self.env['garment.buyer.contact'].search_count(
                [('buyer_id', '=', buyer.id), ('email', '=', self.email)]):
            self.env['garment.buyer.contact'].create({
                'buyer_id': buyer.id, 'name': self.contact_person, 'designation': self.requested_role,
                'department': self.department, 'email': self.email, 'mobile': self.phone,
            })
        return partner

    def _grant_portal_access(self, partner):
        """Grant real Odoo portal access using the standard portal invite wizard
        (creates the res.users if needed and sends the invitation/welcome email)."""
        self.ensure_one()
        wizard = self.env['portal.wizard'].with_context(active_ids=partner.ids).create({})
        for wizard_user in wizard.user_ids.filtered(lambda u: u.partner_id == partner):
            wizard_user.write({'in_portal': True, 'email': wizard_user.email or partner.email})
        wizard.action_apply()
