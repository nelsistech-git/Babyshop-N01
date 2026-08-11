# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
import datetime

class TokenPerDay(models.Model):
    _name = "token.perday"
    _description = "Token Perday"

    name = fields.Char(string="Name")
    sequence_id = fields.Many2one('ir.sequence', string='Kitchen Order IDs Sequence', readonly=True,
                  help="This sequence is automatically created by Odoo but you can change it "
                  "to customize the reference numbers of your kitchen orders.", copy=False, ondelete='restrict')
    date_token = fields.Date(string="Date for Token Sequence", default=datetime.date.today())

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            IrSequence = self.env['ir.sequence'].sudo()
            val = {
                'name': _('POS Kitchen Order %s') % values.get('name'),
                'padding': 4,
                'prefix': "#",
                'code': "pos.screen.config",
            }
            sequence = IrSequence.create(val)
            values['sequence_id'] = sequence.id
        res = super(TokenPerDay, self).create(vals_list)
        return res

    def reset_tokens(self):
        self.search([]).unlink()
