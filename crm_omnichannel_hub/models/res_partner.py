# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_click_to_call(self):
        self.ensure_one()
        return self.env['crm.call.log'].action_click_to_call(
            partner_id=self.id,
            phone_number=self.phone or self.mobile,
        )
