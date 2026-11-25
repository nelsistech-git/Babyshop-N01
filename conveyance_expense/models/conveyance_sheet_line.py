import base64
import binascii
import os

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


_ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
         'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen',
         'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _below_hundred(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + ' ' + _ONES[n % 10]).strip()


def _below_thousand(n):
    words = []
    if n >= 100:
        words.append(_ONES[n // 100] + ' Hundred')
        n %= 100
    if n:
        words.append(_below_hundred(n))
    return ' '.join(words)


def _int_to_words_bd(n):
    """Bangladeshi numbering: Thousand, Lakh, Crore."""
    if n == 0:
        return 'Zero'
    parts = []
    for unit, size in (('Crore', 10000000), ('Lakh', 100000), ('Thousand', 1000)):
        if n >= size:
            parts.append(_int_to_words_bd(n // size) + ' ' + unit)
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return ' '.join(parts)


def _amount_to_words_bdt(amount):
    """1250.5 -> 'One Thousand Two Hundred Fifty Taka and Fifty Paisa Only'"""
    amount = round(amount or 0.0, 2)
    taka = int(amount)
    paisa = int(round((amount - taka) * 100))
    words = _int_to_words_bd(taka) + ' Taka'
    if paisa:
        words += ' and ' + _int_to_words_bd(paisa) + ' Paisa'
    return words + ' Only'


class ConveyanceSheetLine(models.Model):
    _name = 'conveyance.sheet.line'
    _description = 'Conveyance Sheet Line'
    _order = 'date asc, id asc'

    sheet_id = fields.Many2one('conveyance.sheet', string='Conveyance Sheet', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    from_location = fields.Char(string='From')
    to_location = fields.Char(string='To')
    purpose = fields.Char(string='Purpose')
    transport = fields.Selection([
        ('rickshaw', 'Rickshaw'),
        ('cng', 'CNG'),
        ('uber', 'Uber'),
        ('bus', 'Bus'),
        ('pathao', 'Pathao'),
        ('metro_rail', 'Metro Rail'),
        ('car', 'Car'),
        ('walked', 'Walked'),
        ('others', 'Others'),
    ], string='Transport')
    customer_id = fields.Many2one('res.partner', string='Customer')
    category_id = fields.Many2one(
        'product.product',
        string='Category',
        domain=[('can_be_expensed', '=', True)],
    )
    conveyance_amount = fields.Float(string='Conveyance Amount', digits=(12, 2))
    others_cost = fields.Char(string='Others Cost')
    amount = fields.Float(string='Amount', digits=(12, 2))
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        digits=(12, 2),
    )
    remarks = fields.Char(string='Remarks')
    food_bill = fields.Float(string='Food Bill', digits=(12, 2))

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'conveyance_sheet_line_attachment_rel',
        'line_id',
        'attachment_id',
        string='Attachment',
        help='Memo, receipt or report for this line',
    )

    # ---- Receipt reference + receipt file (PDF / JPG only) ----
    x_receipt_attachment = fields.Binary(
        string='Receipt', attachment=True,
        help='Only PDF and JPG/JPEG files are accepted.')
    x_receipt_filename = fields.Char(string='Receipt File Name')
    x_receipt_reference = fields.Char(string='Invoice/Bill/Money Receipt Reference No')

    amount_in_words = fields.Char(
        string='Amount in Word',
        compute='_compute_amount_in_words',
    )

    @api.depends('total_amount')
    def _compute_amount_in_words(self):
        for rec in self:
            rec.amount_in_words = _amount_to_words_bdt(rec.total_amount)

    @api.depends('conveyance_amount', 'food_bill', 'amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.conveyance_amount + rec.food_bill + rec.amount

    @api.constrains('x_receipt_attachment', 'x_receipt_filename')
    def _check_x_receipt_attachment(self):
        for line in self:
            if not line.x_receipt_attachment:
                continue
            name = (line.x_receipt_filename or '').strip().lower()
            if name and os.path.splitext(name)[1] not in ('.pdf', '.jpg', '.jpeg'):
                raise ValidationError(_(
                    "Receipt '%s' is not allowed. Only PDF and JPG/JPEG files can be attached.",
                    line.x_receipt_filename))
            try:
                head = base64.b64decode(line.x_receipt_attachment[:24])
            except (binascii.Error, ValueError):
                raise ValidationError(_("The receipt file is not valid."))
            if not (head.startswith(b'%PDF') or head.startswith(b'\xff\xd8\xff')):
                raise ValidationError(_("The receipt must be a real PDF or JPG/JPEG file."))
