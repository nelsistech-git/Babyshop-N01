# -*- coding: utf-8 -*-
import datetime
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

date_format = "%Y-%m-%d"


class HrResignationNoticePeriodSetting(models.Model):
    _name = 'hr.resignation.notice.period.setting'
    _description = 'HR Separation Notice Period Setting'

    days = fields.Integer(string='Days', default=0, required=True)
    particular = fields.Float(string='Percentage(%) of Gross Salary', default=0, required=True)

    _sql_constraints = [
        ('unique_days', 'unique (days)', 'Days must be unique!'),
        ('unique_particular', 'unique (particular)', 'Percentage must be unique!')]