# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models
from odoo.tools import file_open

# Text printed on the universal letterhead pad (Letter_Head_Pad1.pdf)
LH_REGISTERED = 'House # B-1 (First Floor), Plot # 11/A-1, Gulshan -2, Dhaka-1212'
LH_CORPORATE = ('Sattar Bhaban, Plot- 224 & 226, Bogabari Bazaar, Alia Madrasha, '
                'Ashulia, Dhaka-1349, Bangladesh')
LH_PHONE = '+8801911908653'
LH_EMAIL = 'bbbl@mtailor.com'
LH_WEBSITE = 'www.mtailor.com'


def _default_letterhead_logo():
    try:
        with file_open('custom_account_day_book/static/src/img/mtailor_logo.png', 'rb') as f:
            return base64.b64encode(f.read())
    except Exception:
        return False


class ResCompany(models.Model):
    _inherit = 'res.company'

    letterhead_name = fields.Char(string='Letterhead Title', default='Bit Body Bangladesh Limited')
    letterhead_logo = fields.Binary(
        string='Letterhead Logo', default=lambda self: _default_letterhead_logo(),
        help='Optional. When empty, the built-in MTAILOR logo box is printed.')
    letterhead_registered_office = fields.Char(string='Registered Office', default=LH_REGISTERED)
    letterhead_corporate_office = fields.Char(string='Corporate & Factory Office', default=LH_CORPORATE)
    letterhead_phone = fields.Char(string='Letterhead Phone', default=LH_PHONE)
    letterhead_email = fields.Char(string='Letterhead Email', default=LH_EMAIL)
    letterhead_website = fields.Char(string='Letterhead Website', default=LH_WEBSITE)

    @api.model
    def _fill_letterhead_defaults(self):
        """Fill every EMPTY letterhead field (existing companies never got the field defaults)."""
        defaults = {
            'letterhead_name': 'Bit Body Bangladesh Limited',
            'letterhead_registered_office': LH_REGISTERED,
            'letterhead_corporate_office': LH_CORPORATE,
            'letterhead_phone': LH_PHONE,
            'letterhead_email': LH_EMAIL,
            'letterhead_website': LH_WEBSITE,
        }
        logo = _default_letterhead_logo()
        if logo:
            defaults['letterhead_logo'] = logo
        for company in self.sudo().search([]):
            vals = {k: v for k, v in defaults.items() if not company[k]}
            if vals:
                company.write(vals)

    # ---- enforce one universal letterhead / paper format -----------------------------------
    @api.model
    def _mtailor_layout_vals(self):
        layout = self.env.ref('custom_account_day_book.external_layout_mtailor', raise_if_not_found=False)
        paperformat = self.env.ref('custom_account_day_book.paperformat_mtailor', raise_if_not_found=False)
        vals = {}
        if layout:
            vals['external_report_layout_id'] = layout.id
        if paperformat:
            vals['paperformat_id'] = paperformat.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        forced = self._mtailor_layout_vals()
        vals_list = [dict(vals, **forced) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if 'external_report_layout_id' in vals or 'paperformat_id' in vals:
            vals = dict(vals, **self._mtailor_layout_vals())
        return super().write(vals)
