# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import pytz

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import AccessError
# from odoo.tools.float_utils import float_round
from odoo.tools import float_compare, float_round, float_repr


_logger = logging.getLogger(__name__)



class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_investment = fields.Boolean(string="Is Investment?")



class AccountMove(models.Model):
    _inherit = 'account.move'


    is_collection = fields.Boolean(string="Is Collection?")

    