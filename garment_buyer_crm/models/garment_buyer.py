# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. See LICENSE file for full copyright
# and licensing details. Copyright (c) Nelsis Tech (www.nelsistech.com)

import pytz  # FIXED: Added pytz import for timezone list
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GarmentBuyer(models.Model):
    """Buyer 360 master — central record for every garment buyer / buying house.

    Linked 1-to-1 with res.partner so the buyer can flow straight into Sales,
    Invoicing and Portal access, while keeping garment-industry-specific data
    (compliance certificates, buying preferences, buyer lifecycle status...)
    on its own model as specified in the Buyer CRM SRS.
    """
    _name = 'garment.buyer'
    _description = 'Garment Buyer (Buyer 360)'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'name'
    _rec_name = 'name'

    # ---------------------------------------------------------------------
    # Basic Information
    # ---------------------------------------------------------------------
    buyer_code = fields.Char(string='Buyer Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Buyer Name', required=True, tracking=True)
    legal_name = fields.Char(string='Legal Name')
    brand_name = fields.Char(string='Brand Name')
    partner_id = fields.Many2one('res.partner', string='Related Contact', ondelete='restrict',
                                  help='Underlying res.partner record used for Sales/Invoicing/Portal.')
    buyer_category = fields.Selection([
        ('direct_buyer', 'Direct Buyer'),
        ('buying_house', 'Buying House'),
        ('brand_owner', 'Brand Owner'),
        ('retail_chain', 'Retail Chain'),
        ('importer', 'Importer'),
        ('wholesaler', 'Wholesaler'),
        ('online_retailer', 'Online Retailer'),
        ('private_label', 'Private Label Buyer'),
        ('government', 'Government Buyer'),
        ('ngo', 'NGO Buyer'),
        ('distributor', 'Distributor'),
        ('franchise', 'Franchise Buyer'),
    ], string='Buyer Category', tracking=True)
    buyer_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('export', 'Export'),
        ('international', 'International'),
        ('vip', 'VIP'),
        ('strategic', 'Strategic'),
        ('key_account', 'Key Account'),
        ('seasonal', 'Seasonal'),
        ('high_volume', 'High Volume'),
        ('small_order', 'Small Order'),
        ('sample_only', 'Sample Only'),
    ], string='Buyer Type')
    industry = fields.Char(string='Industry')
    registration_number = fields.Char(string='Registration Number')
    vat_number = fields.Char(string='VAT Number')
    tax_number = fields.Char(string='Tax Number')
    bin_number = fields.Char(string='BIN Number')
    website = fields.Char(string='Website')
    logo = fields.Binary(string='Company Logo', attachment=True)
    branch = fields.Char(string='Branch', help='Servicing branch/office for multi-branch companies.')
    bgmea_reference = fields.Char(string='BGMEA Reference',
                                   help='Bangladesh Garment Manufacturers and Exporters Association reference.')
    bkmea_reference = fields.Char(string='BKMEA Reference',
                                   help='Bangladesh Knitwear Manufacturers and Exporters Association reference.')
    tag_ids = fields.Many2many('garment.crm.tag', string='Tags')
    internal_notes = fields.Text(string='Internal Notes')

    buyer_status = fields.Selection([
        ('new_lead', 'New Lead'),
        ('contacted', 'Contacted'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('interested', 'Interested'),
        ('rfq_received', 'RFQ Received'),
        ('quotation_sent', 'Quotation Sent'),
        ('negotiation', 'Negotiation'),
        ('sampling', 'Sampling'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active Buyer'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ], string='Buyer Status', default='new_lead', tracking=True, group_expand='_expand_states')

    lead_source_id = fields.Many2one('garment.lead.source', string='Lead Source', tracking=True)
    assigned_merchandiser_id = fields.Many2one('res.users', string='Assigned Merchandiser')
    marketing_executive_id = fields.Many2one('res.users', string='Marketing Executive')

    # ---------------------------------------------------------------------
    # Contact Information
    # ---------------------------------------------------------------------
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='State')
    city = fields.Char(string='City')
    zip = fields.Char(string='Postal Code')
    street = fields.Char(string='Address Line 1')
    street2 = fields.Char(string='Address Line 2')
    google_map_url = fields.Char(string='Google Map Location')
    tz = fields.Selection('_tz_get', string='Time Zone')
    phone = fields.Char(string='Office Phone')
    mobile = fields.Char(string='Mobile')
    whatsapp = fields.Char(string='WhatsApp')
    email = fields.Char(string='Email')
    email_secondary = fields.Char(string='Secondary Email')
    skype = fields.Char(string='Skype')
    wechat = fields.Char(string='WeChat')
    linkedin = fields.Char(string='LinkedIn')
    facebook = fields.Char(string='Facebook')
    instagram = fields.Char(string='Instagram')

    # FIXED: Replaced env['res.users']._tz_get() with direct pytz.all_timezones call
    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in pytz.all_timezones]

    # ---------------------------------------------------------------------
    # Business Information
    # ---------------------------------------------------------------------
    annual_purchase_volume = fields.Monetary(string='Annual Purchase Volume', currency_field='currency_id')
    annual_revenue = fields.Monetary(string='Annual Revenue', currency_field='currency_id')
    employee_count = fields.Integer(string='Employee Count')
    store_count = fields.Integer(string='Number of Stores')
    currency_id = fields.Many2one('res.currency', string='Preferred Currency',
                                   default=lambda s: s.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    preferred_shipment_method = fields.Selection([
        ('sea', 'Sea Freight'), ('air', 'Air Freight'), ('road', 'Road'), ('rail', 'Rail'), ('courier', 'Courier'),
    ], string='Preferred Shipment Method')
    preferred_port = fields.Char(string='Preferred Port')
    preferred_fabric_type = fields.Char(string='Preferred Fabric Type')
    preferred_product_category = fields.Char(string='Preferred Product Category')
    moq = fields.Integer(string='MOQ (pcs)')
    compliance_requirements = fields.Text(string='Compliance Requirements')
    preferred_quality_level = fields.Selection([
        ('standard', 'Standard'), ('premium', 'Premium'), ('luxury', 'Luxury'),
    ], string='Preferred Quality Level')

    # ---------------------------------------------------------------------
    # Financial Information
    # ---------------------------------------------------------------------
    credit_limit = fields.Monetary(string='Credit Limit', currency_field='currency_id')
    outstanding_balance = fields.Monetary(string='Outstanding Balance', currency_field='currency_id',
                                           compute='_compute_outstanding_balance')
    credit_days = fields.Integer(string='Credit Days')
    risk_rating = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Risk Rating', default='low')
    insurance_provider = fields.Char(string='Insurance Provider')
    bank_name = fields.Char(string='Bank Information')
    swift_code = fields.Char(string='SWIFT Code')
    lc_bank = fields.Char(string='LC Bank')
    currency_exposure = fields.Char(string='Currency Exposure')

    def _compute_outstanding_balance(self):
        for rec in self:
            rec.outstanding_balance = rec.partner_id.total_due if rec.partner_id else 0.0

    # ---------------------------------------------------------------------
    # Compliance Information (certificates held by the buyer / required of us)
    # ---------------------------------------------------------------------
    cert_bsci = fields.Boolean(string='BSCI')
    cert_sedex = fields.Boolean(string='SEDEX')
    cert_wrap = fields.Boolean(string='WRAP')
    cert_gots = fields.Boolean(string='GOTS')
    cert_ocs = fields.Boolean(string='OCS')
    cert_oeko_tex = fields.Boolean(string='OEKO-TEX')
    cert_higg = fields.Boolean(string='HIGG Index')
    cert_iso = fields.Boolean(string='ISO')
    cert_rcs = fields.Boolean(string='RCS')
    cert_grs = fields.Boolean(string='GRS')
    cert_fsc = fields.Boolean(string='FSC')
    custom_compliance_note = fields.Char(string='Custom Compliance Certificates')

    # ---------------------------------------------------------------------
    # Buying Preferences
    # ---------------------------------------------------------------------
    preferred_fabric = fields.Char(string='Preferred Fabric')
    preferred_gsm = fields.Char(string='Preferred GSM')
    preferred_color = fields.Char(string='Preferred Color')
    preferred_printing = fields.Char(string='Preferred Printing')
    preferred_embroidery = fields.Char(string='Preferred Embroidery')
    preferred_packaging = fields.Char(string='Preferred Packaging')
    preferred_label = fields.Char(string='Preferred Label')
    preferred_accessories = fields.Char(string='Preferred Accessories')
    sustainability_preference = fields.Char(string='Sustainability Preference')
    recycled_material_required = fields.Boolean(string='Recycled Material Requirement')

    # ---------------------------------------------------------------------
    # Communication Preferences
    # ---------------------------------------------------------------------
    preferred_language = fields.Char(string='Preferred Language')
    preferred_contact_time = fields.Char(string='Preferred Contact Time')
    preferred_channel = fields.Selection([
        ('email', 'Email'), ('phone', 'Phone'), ('whatsapp', 'WhatsApp'),
        ('zoom', 'Zoom'), ('teams', 'MS Teams'), ('in_person', 'In Person'),
    ], string='Preferred Communication Channel')
    email_frequency = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('as_needed', 'As Needed'),
    ], string='Email Frequency')
    marketing_consent = fields.Boolean(string='Marketing Consent')
    nda_signed = fields.Boolean(string='NDA Signed')
    nda_expiry_date = fields.Date(string='NDA Expiry Date')
    data_sharing_consent = fields.Boolean(string='Data Sharing Consent')

    # ---------------------------------------------------------------------
    # Buyer Segmentation (SRS section 21)
    # ---------------------------------------------------------------------
    business_segment = fields.Selection([
        ('knit', 'Knit'), ('woven', 'Woven'), ('sweater', 'Sweater'), ('denim', 'Denim'),
        ('home_textile', 'Home Textile'), ('sportswear', 'Sportswear'), ('outerwear', 'Outerwear'),
        ('lingerie', 'Lingerie'), ('uniform', 'Uniform'),
    ], string='Business Segment')
    volume_segment = fields.Selection([
        ('small', 'Small'), ('medium', 'Medium'), ('large', 'Large'), ('enterprise', 'Enterprise'),
    ], string='Volume Segment')
    profitability_segment = fields.Selection([
        ('high_margin', 'High Margin'), ('medium_margin', 'Medium Margin'), ('low_margin', 'Low Margin'),
    ], string='Profitability Segment')

    # ---------------------------------------------------------------------
    # Buyer Registration Approval Workflow (SRS section 39)
    # ---------------------------------------------------------------------
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('sales_executive', 'Sales Executive Review'),
        ('marketing_manager', 'Marketing Manager Review'),
        ('general_manager', 'General Manager Review'),
        ('managing_director', 'Managing Director Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True, copy=False)
    approval_date = fields.Date(string='Approval Date', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    is_buyer_activated = fields.Boolean(string='Buyer Activated', compute='_compute_is_buyer_activated', store=True)

    # ---------------------------------------------------------------------
    # Relations
    # ---------------------------------------------------------------------
    contact_ids = fields.One2many('garment.buyer.contact', 'buyer_id', string='Buyer Contacts')
    document_ids = fields.One2many('garment.buyer.document', 'buyer_id', string='Buyer Documents')
    communication_ids = fields.One2many('garment.buyer.communication', 'buyer_id', string='Communication Log')
    opportunity_ids = fields.One2many('garment.opportunity', 'buyer_id', string='Opportunities')
    rfq_ids = fields.One2many('garment.rfq', 'buyer_id', string='RFQs')
    meeting_ids = fields.One2many('garment.crm.meeting', 'buyer_id', string='Meetings')
    visit_ids = fields.One2many('garment.buyer.visit', 'buyer_id', string='Factory Visits')
    complaint_ids = fields.One2many('garment.buyer.complaint', 'buyer_id', string='Complaints')
    activity_schedule_ids = fields.One2many('garment.crm.activity', 'buyer_id', string='Scheduled Activities')

    opportunity_count = fields.Integer(compute='_compute_counts')
    rfq_count = fields.Integer(compute='_compute_counts')
    communication_count = fields.Integer(compute='_compute_counts')
    meeting_count = fields.Integer(compute='_compute_counts')
    visit_count = fields.Integer(compute='_compute_counts')
    complaint_count = fields.Integer(compute='_compute_counts')

    # ---------------------------------------------------------------------
    # AI Assist
    # ---------------------------------------------------------------------
    ai_lead_score = fields.Float(string='AI Lead Score', readonly=True, tracking=True,
                                  help='0-100 propensity-to-convert score generated by the AI engine.')
    ai_score_classification = fields.Selection([
        ('platinum', 'Platinum (90-100)'),
        ('gold', 'Gold (80-89)'),
        ('silver', 'Silver (70-79)'),
        ('bronze', 'Bronze (50-69)'),
        ('low_potential', 'Low Potential (<50)'),
    ], string='AI Score Classification', compute='_compute_ai_score_classification', store=True)
    ai_last_insight = fields.Text(string='AI Insight', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    last_activity_date = fields.Date(string='Last Activity Date', compute='_compute_last_activity_date',
                                      store=True, help='Most recent communication/RFQ/opportunity date — used to '
                                                        'flag dormant buyers (SRS section 32/40).')
    is_dormant = fields.Boolean(string='Inactive (No Activity)', default=False, tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('buyer_code_uniq', 'unique(buyer_code, company_id)', 'Buyer Code must be unique per company!'),
    ]

    @api.depends('opportunity_ids', 'rfq_ids', 'communication_ids', 'meeting_ids', 'visit_ids', 'complaint_ids')
    def _compute_counts(self):
        for rec in self:
            rec.opportunity_count = len(rec.opportunity_ids)
            rec.rfq_count = len(rec.rfq_ids)
            rec.communication_count = len(rec.communication_ids)
            rec.meeting_count = len(rec.meeting_ids)
            rec.visit_count = len(rec.visit_ids)
            rec.complaint_count = len(rec.complaint_ids)

    @api.depends('ai_lead_score')
    def _compute_ai_score_classification(self):
        for rec in self:
            score = rec.ai_lead_score or 0.0
            if score >= 90:
                rec.ai_score_classification = 'platinum'
            elif score >= 80:
                rec.ai_score_classification = 'gold'
            elif score >= 70:
                rec.ai_score_classification = 'silver'
            elif score >= 50:
                rec.ai_score_classification = 'bronze'
            else:
                rec.ai_score_classification = 'low_potential'

    @api.depends('approval_status')
    def _compute_is_buyer_activated(self):
        for rec in self:
            rec.is_buyer_activated = rec.approval_status == 'approved'

    @api.depends('communication_ids.date', 'opportunity_ids.create_date', 'rfq_ids.rfq_date')
    def _compute_last_activity_date(self):
        for rec in self:
            candidates = []
            if rec.communication_ids:
                candidates.append(max(rec.communication_ids.mapped('date')))
            if rec.rfq_ids:
                candidates.append(max(rec.rfq_ids.mapped('rfq_date')))
            if rec.opportunity_ids:
                create_dates = [d for d in rec.opportunity_ids.mapped('create_date') if d]
                if create_dates:
                    candidates.append(max(create_dates))
            dates = []
            for c in candidates:
                dates.append(c.date() if hasattr(c, 'date') else c)
            rec.last_activity_date = max(dates) if dates else False

    def _expand_states(self, states, domain, order=None):
        return [key for key, _val in self._fields['buyer_status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('buyer_code', _('New')) == _('New'):
                vals['buyer_code'] = self.env['ir.sequence'].next_by_code('garment.buyer') or _('New')
        return super().create(vals_list)

    def action_create_related_partner(self):
        """Create/link a res.partner so the buyer can be used in Sales & Invoicing."""
        Partner = self.env['res.partner']
        for rec in self:
            if rec.partner_id:
                continue
            partner = Partner.create({
                'name': rec.name,
                'is_company': True,
                'email': rec.email,
                'phone': rec.phone,
                'mobile': rec.mobile,
                'street': rec.street,
                'street2': rec.street2,
                'city': rec.city,
                'zip': rec.zip,
                'country_id': rec.country_id.id,
                'state_id': rec.state_id.id,
                'website': rec.website,
                'customer_rank': 1,
            })
            rec.partner_id = partner.id
        return True

    def action_view_opportunities(self):
        self.ensure_one()
        return {
            'name': _('Opportunities'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.opportunity',
            'view_mode': 'kanban,tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_rfqs(self):
        self.ensure_one()
        return {
            'name': _('RFQs'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.rfq',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_meetings(self):
        self.ensure_one()
        return {
            'name': _('Meetings'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.crm.meeting',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_visits(self):
        self.ensure_one()
        return {
            'name': _('Factory Visits'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.buyer.visit',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_complaints(self):
        self.ensure_one()
        return {
            'name': _('Complaints'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.buyer.complaint',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    # ------------------------------------------------------------------
    # Buyer Registration Approval Workflow (SRS section 39)
    # Draft -> Sales Executive -> Marketing Manager -> General Manager ->
    # Managing Director -> Approved -> Buyer Activated
    # ------------------------------------------------------------------
    _APPROVAL_SEQUENCE = ['draft', 'sales_executive', 'marketing_manager', 'general_manager',
                           'managing_director', 'approved']

    def action_submit_for_approval(self):
        for rec in self:
            if rec.approval_status in ('draft', 'rejected'):
                rec.approval_status = 'sales_executive'

    def action_approval_advance(self):
        """Move the buyer registration one step forward in the approval chain."""
        for rec in self:
            sequence = rec._APPROVAL_SEQUENCE
            if rec.approval_status not in sequence:
                continue
            idx = sequence.index(rec.approval_status)
            if idx >= len(sequence) - 1:
                continue
            next_status = sequence[idx + 1]
            vals = {'approval_status': next_status}
            if next_status == 'approved':
                vals.update({
                    'approval_date': fields.Date.context_today(rec),
                    'approved_by_id': self.env.user.id,
                })
                if rec.buyer_status == 'new_lead':
                    vals['buyer_status'] = 'active'
            rec.write(vals)

    def action_reject_approval(self):
        self.write({'approval_status': 'rejected'})

    def action_run_ai_analysis(self):
        """Trigger the AI engine to (re)score this buyer and store an insight."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            score, insight = ai_engine.score_buyer(rec)
            rec.write({
                'ai_lead_score': score,
                'ai_last_insight': insight,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    @api.constrains('email', 'email_secondary')
    def _check_email_format(self):
        for rec in self:
            for value in (rec.email, rec.email_secondary):
                if value and '@' not in value:
                    raise ValidationError(_('Please enter a valid email address for %s.') % rec.name)

    # ------------------------------------------------------------------
    # Automation Rules (SRS section 40)
    # ------------------------------------------------------------------
    @api.model
    def _cron_score_all_active_leads(self):
        """Nightly job: 'Calculate lead scores nightly'."""
        buyers = self.search([('buyer_status', 'not in', ['inactive', 'blacklisted'])])
        buyers.action_run_ai_analysis()

    @api.model
    def _cron_flag_inactive_buyers(self, inactivity_days=90):
        """'Archive inactive leads after configurable inactivity' /
        'Inactive Buyer (No Activity)' notification."""
        threshold = fields.Date.context_today(self) - timedelta(days=inactivity_days)
        buyers = self.search([('buyer_status', 'not in', ['inactive', 'blacklisted'])])
        for buyer in buyers:
            was_dormant = buyer.is_dormant
            is_dormant = bool(buyer.last_activity_date and buyer.last_activity_date < threshold)
            if is_dormant != was_dormant:
                buyer.is_dormant = is_dormant
                if is_dormant:
                    buyer.message_post(body=_('Buyer has had no recorded activity since %s and has been '
                                               'flagged as inactive.') % buyer.last_activity_date)

    @api.model
    def _cron_notify_nda_expiry(self, reminder_days=30):
        """'NDA Expiry' notification (SRS section 32)."""
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=reminder_days)
        buyers = self.search([
            ('nda_expiry_date', '!=', False),
            ('nda_expiry_date', '<=', limit),
            ('nda_expiry_date', '>=', today),
        ])
        for buyer in buyers:
            buyer.message_post(body=_('NDA is expiring on %s.') % buyer.nda_expiry_date)
