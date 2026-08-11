# -*- coding: utf-8 -*-
import logging
import random
import string
import uuid
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import qrcode
    import io
    import base64
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class ExpressLoyaltyCard(models.Model):
    _name = 'express.loyalty.card'
    _description = 'Express POS Loyalty Membership Card'
    _rec_name = 'card_code'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    brand_id = fields.Many2one('express.pos.brand')
    card_code = fields.Char(readonly=True, copy=False, default=lambda self: self._generate_card_code())
    qr_image = fields.Binary(compute='_compute_qr_image', store=True, attachment=True)
    points = fields.Float(default=0.0)
    mobile = fields.Char(related='partner_id.mobile', readonly=False)
    mobile_verified = fields.Boolean(default=False, copy=False)
    otp_code = fields.Char(copy=False)
    otp_expiry = fields.Datetime(copy=False)
    active = fields.Boolean(default=True)
    issue_date = fields.Date(default=fields.Date.context_today)

    _sql_constraints = [
        ('card_code_uniq', 'unique(card_code)', 'Loyalty card code must be unique.'),
    ]

    @api.model
    def _generate_card_code(self):
        return 'LC-' + uuid.uuid4().hex[:10].upper()

    @api.depends('card_code')
    def _compute_qr_image(self):
        for rec in self:
            if not rec.card_code:
                rec.qr_image = False
                continue
            if QRCODE_AVAILABLE:
                try:
                    img = qrcode.make(rec.card_code)
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    rec.qr_image = base64.b64encode(buf.getvalue())
                    continue
                except Exception:
                    _logger.warning('QR generation failed for card %s, falling back to text code.', rec.card_code)
            rec.qr_image = False

    # ------------------------------------------------------------------
    # OTP verification (stub gateway - wire to your SMS provider's HTTP API
    # in _send_otp_sms; interface/config kept real, transport is a placeholder).
    # ------------------------------------------------------------------
    def action_generate_otp(self):
        self.ensure_one()
        otp = ''.join(random.choices(string.digits, k=6))
        self.otp_code = otp
        self.otp_expiry = fields.Datetime.now() + timedelta(minutes=5)
        self._send_otp_sms(self.mobile, otp)
        return True

    def _send_otp_sms(self, mobile, otp):
        """Placeholder SMS gateway call. Replace with a real HTTP request to your
        SMS aggregator (e.g. an operator API) once credentials are available."""
        _logger.info('[STUB SMS GATEWAY] Would send OTP %s to %s', otp, mobile)
        return True

    def action_verify_otp(self, code):
        self.ensure_one()
        if not self.otp_code or not self.otp_expiry:
            raise UserError(_('No OTP has been generated for this card.'))
        if fields.Datetime.now() > self.otp_expiry:
            raise UserError(_('OTP has expired. Please request a new one.'))
        if code != self.otp_code:
            raise UserError(_('Incorrect OTP.'))
        self.mobile_verified = True
        self.otp_code = False
        return True

    def add_points(self, amount_spent, rate=None):
        self.ensure_one()
        if rate is None:
            rate = float(self.env['ir.config_parameter'].sudo().get_param('express_retail_pos.loyalty_point_rate', '100'))
        if rate <= 0:
            return
        earned = amount_spent / rate
        self.points += earned
        return earned


class ExpressLoyaltyRule(models.Model):
    _name = 'express.loyalty.rule'
    _description = 'Express POS Discount / Offer Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    rule_type = fields.Selection([
        ('style', 'Style Number-wise Discount'),
        ('showroom', 'Showroom Location-wise Discount'),
        ('total_bill', 'Total Shopping Bill-wise Discount'),
        ('bogo', 'Buy X Get Y (e.g. Buy 1 Get 1 / Buy 2 Get 1)'),
    ], required=True)

    brand_id = fields.Many2one('express.pos.brand')
    branch_id = fields.Many2one('express.pos.branch')

    style_number = fields.Char(help='Matched against the product\'s Style Number field.')
    min_amount = fields.Float(string='Minimum Bill Amount', help='For total bill-wise tiers.')
    discount_percent = fields.Float(help='Discount % applied when this rule matches.')

    buy_qty = fields.Integer(string='Buy Quantity', default=1)
    get_qty = fields.Integer(string='Get Free Quantity', default=1)
    get_discount_percent = fields.Float(default=100.0, help='Discount % on the free units, typically 100%.')
    bogo_product_id = fields.Many2one('product.product', string='Applies to Product (leave empty for any product in scope)')

    date_from = fields.Date()
    date_to = fields.Date()

    def _is_active_today(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_from and today < rec.date_from:
                return False
            if rec.date_to and today > rec.date_to:
                return False
        return True


class ExpressGiftCard(models.Model):
    _name = 'express.gift.card'
    _description = 'Express POS Gift Card'
    _rec_name = 'code'

    code = fields.Char(readonly=True, copy=False, default=lambda self: self._generate_code())
    brand_id = fields.Many2one('express.pos.brand')
    partner_id = fields.Many2one('res.partner', string='Issued To')
    initial_amount = fields.Monetary(required=True)
    balance = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    issue_date = fields.Date(default=fields.Date.context_today)
    expiry_date = fields.Date()
    state = fields.Selection([
        ('active', 'Active'),
        ('used', 'Fully Used'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='active')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Gift card code must be unique.'),
    ]

    @api.model
    def _generate_code(self):
        return 'GC-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    @api.model
    def create(self, vals):
        if 'balance' not in vals and 'initial_amount' in vals:
            vals['balance'] = vals['initial_amount']
        return super().create(vals)

    def redeem(self, amount):
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('This gift card is not active.'))
        if self.expiry_date and fields.Date.context_today(self) > self.expiry_date:
            self.state = 'expired'
            raise UserError(_('This gift card has expired.'))
        if amount > self.balance:
            raise UserError(_('Insufficient gift card balance. Available: %.2f') % self.balance)
        self.balance -= amount
        if self.balance <= 0.0001:
            self.state = 'used'
        return True
