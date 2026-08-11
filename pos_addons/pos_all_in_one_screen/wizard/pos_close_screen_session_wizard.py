#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
from odoo import models

class PosCloseScreenSessionWizard(models.TransientModel):
    _name = "pos.close.screen.session.wizard"
    _description = "Close POS Screen Session Wizard"

    def close_screen_session(self):
        order = self.env["pos.kitchen.order"]
        return order.done_pending_order(self.env.context["session_id"])
