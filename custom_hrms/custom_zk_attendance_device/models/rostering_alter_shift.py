from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class RosteringAlterShift(models.Model):
    _name = "rostering.alter.shift"
    _description = "Rostering Alter Shift"
    _rec_name = 'from_employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # name = fields.Char(string='Name', reuired=True)
    from_employee_id = fields.Many2one('hr.employee', string='From Employee', required=True, tracking=True)
    to_employee_id = fields.Many2one('hr.employee', string='To Employee', required=True, tracking=True)
    err_msg_from = fields.Char(string='Warning')
    err_msg_to = fields.Char(string='Warning')
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    from_shift_ids = fields.Many2many('rostering.shift.settings', 'relation_table_one1', 'col1', 'col2', string="Current Shift")
    to_shift_ids = fields.Many2many('rostering.shift.settings', 'relation_table_two2', 'col1', 'col2', string="Current Shift")
    shift_ids = fields.Many2many('rostering.shift.settings', string="Shift")
    date = fields.Date(string='Date', tracking=True, default=fields.Date.context_today, required=True)
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month')
    # shift_id = fields.Many2many('rostering.shift.settings')
    remarks = fields.Text(string='Remarks',tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')

    @api.onchange('department_id')
    def onchange_department_id(self):
        if self.department_id:
            return {'domain': {'from_employee_id': [('department_id', '=', self.department_id.id), ('active', '=', True)], 'to_employee_id': [('department_id', '=', self.department_id.id), ('active', '=', True)]}}
        else:
            return {'domain': {'from_employee_id': [('active', '=', True)], 'to_employee_id': [('active', '=', True)]}}

    @api.onchange('from_employee_id', 'date', 'department_id')
    def _onchange_from_employee_id(self):
        if self.date and self.from_employee_id:
            date_str = str(self.date)
            self.from_shift_ids = None
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_str = date_obj.strftime('%d')

            # Get the year and month
            year = date_obj.year
            day = date_obj.day
            month_str = date_obj.strftime('%m')
            month_shift_id = self.env['rostering.monthly.shift'].search([('month', '=', month_str),
                                                                         ('year', '=', year)],
                                                                        limit=1)
            if not month_shift_id:
                self.err_msg_from = self.from_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first'
            else:
                self.err_msg_from = ''
            day_filter = 'day_' + str(day)
            # if month_shift_id and self.from_employee_id:
            #     delay = """select * from rostering_monthly_shift_line where head_id = %s and employee_id = %s"""
            #     self._cr.execute(delay, [month_shift_id.id, self.from_employee_id.id])
            #     record = self.env.cr.dictfetchall()
            #     print(record)

            if month_shift_id and self.from_employee_id:
                month_shift_line_id = self.env['rostering.monthly.shift.line'].search([('head_id', '=', month_shift_id.id),
                                                                             ('employee_id', '=', self.from_employee_id.id)],
                                                                            limit=1)
                if not month_shift_line_id:
                    raise UserError(
                        _(self.from_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first!'))

                err_msg = 'No Shift set for this Employee on This Date'

                if day_filter == 'day_1':
                    if month_shift_line_id.day_1:
                        self.from_shift_ids = month_shift_line_id.day_1
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_2':
                    if month_shift_line_id.day_2:
                        self.from_shift_ids = month_shift_line_id.day_2
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_3':
                    if month_shift_line_id.day_3:
                        self.from_shift_ids = month_shift_line_id.day_3
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_4':
                    if month_shift_line_id.day_4:
                        self.from_shift_ids = month_shift_line_id.day_4
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_5':
                    if month_shift_line_id.day_5:
                        self.from_shift_ids = month_shift_line_id.day_5
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_6':
                    if month_shift_line_id.day_6:
                        self.from_shift_ids = month_shift_line_id.day_6
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_7':
                    if month_shift_line_id.day_7:
                        self.from_shift_ids = month_shift_line_id.day_7
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_8':
                    if month_shift_line_id.day_8:
                        self.from_shift_ids = month_shift_line_id.day_8
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_9':
                    if month_shift_line_id.day_9:
                        self.from_shift_ids = month_shift_line_id.day_9
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_10':
                    if month_shift_line_id.day_10:
                        self.from_shift_ids = month_shift_line_id.day_10
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_11':
                    if month_shift_line_id.day_11:
                        self.from_shift_ids = month_shift_line_id.day_11
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_12':
                    if month_shift_line_id.day_12:
                        self.from_shift_ids = month_shift_line_id.day_12
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_13':
                    if month_shift_line_id.day_13:
                        self.from_shift_ids = month_shift_line_id.day_13
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_14':
                    if month_shift_line_id.day_14:
                        self.from_shift_ids = month_shift_line_id.day_14
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_15':
                    if month_shift_line_id.day_15:
                        self.from_shift_ids = month_shift_line_id.day_15
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_16':
                    if month_shift_line_id.day_16:
                        self.from_shift_ids = month_shift_line_id.day_16
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_17':
                    if month_shift_line_id.day_17:
                        self.from_shift_ids = month_shift_line_id.day_17
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_18':
                    if month_shift_line_id.day_18:
                        self.from_shift_ids = month_shift_line_id.day_18
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_19':
                    if month_shift_line_id.day_19:
                        self.from_shift_ids = month_shift_line_id.day_19
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_20':
                    if month_shift_line_id.day_20:
                        self.from_shift_ids = month_shift_line_id.day_20
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_21':
                    if month_shift_line_id.day_21:
                        self.from_shift_ids = month_shift_line_id.day_21
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_22':
                    if month_shift_line_id.day_22:
                        self.from_shift_ids = month_shift_line_id.day_22
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_23':
                    if month_shift_line_id.day_23:
                        self.from_shift_ids = month_shift_line_id.day_23
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_24':
                    if month_shift_line_id.day_24:
                        self.from_shift_ids = month_shift_line_id.day_24
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_25':
                    if month_shift_line_id.day_25:
                        self.from_shift_ids = month_shift_line_id.day_25
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_26':
                    if month_shift_line_id.day_26:
                        self.from_shift_ids = month_shift_line_id.day_26
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_27':
                    if month_shift_line_id.day_27:
                        self.from_shift_ids = month_shift_line_id.day_27
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_28':
                    if month_shift_line_id.day_28:
                        self.from_shift_ids = month_shift_line_id.day_28
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_29':
                    if month_shift_line_id.day_29:
                        self.from_shift_ids = month_shift_line_id.day_29
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_30':
                    if month_shift_line_id.day_30:
                        self.from_shift_ids = month_shift_line_id.day_30
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                elif day_filter == 'day_31':
                    if month_shift_line_id.day_31:
                        self.from_shift_ids = month_shift_line_id.day_31
                        self.err_msg_from = False
                    else:
                        self.err_msg_from = err_msg
                else:
                    self.err_msg_from = err_msg
    
    @api.onchange('to_employee_id', 'date', 'department_id')
    def _onchange_from_to_employee_id(self):
        if self.date and self.to_employee_id:
            date_str = str(self.date)
            self.to_shift_ids = None
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_str = date_obj.strftime('%d')

            # Get the year and month
            year = date_obj.year
            day = date_obj.day
            month_str = date_obj.strftime('%m')
            month_shift_id = self.env['rostering.monthly.shift'].search([('month', '=', month_str),
                                                                         ('year', '=', year)],
                                                                        limit=1)
            if not month_shift_id:
                self.err_msg_to = self.to_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first'
            else:
                self.err_msg_to = ''

            day_filter = 'day_' + str(day)

            if month_shift_id and self.to_employee_id:
                month_shift_line_id = self.env['rostering.monthly.shift.line'].search([('head_id', '=', month_shift_id.id),
                                                                             ('employee_id', '=', self.to_employee_id.id)],
                                                                            limit=1)
                if not month_shift_line_id:
                    self.err_msg_to = self.to_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first'
                else:
                    self.err_msg_to = False

                if day_filter == 'day_1':
                    if month_shift_line_id.day_1:
                        self.to_shift_ids = month_shift_line_id.day_1
                elif day_filter == 'day_2':
                    if month_shift_line_id.day_2:
                        self.to_shift_ids = month_shift_line_id.day_2
                elif day_filter == 'day_3':
                    if month_shift_line_id.day_3:
                        self.to_shift_ids = month_shift_line_id.day_3
                elif day_filter == 'day_4':
                    if month_shift_line_id.day_4:
                        self.to_shift_ids = month_shift_line_id.day_4
                elif day_filter == 'day_5':
                    if month_shift_line_id.day_5:
                        self.to_shift_ids = month_shift_line_id.day_5
                elif day_filter == 'day_6':
                    if month_shift_line_id.day_6:
                        self.to_shift_ids = month_shift_line_id.day_6
                elif day_filter == 'day_7':
                    if month_shift_line_id.day_7:
                        self.to_shift_ids = month_shift_line_id.day_7
                elif day_filter == 'day_8':
                    if month_shift_line_id.day_8:
                        self.to_shift_ids = month_shift_line_id.day_8
                elif day_filter == 'day_9':
                    if month_shift_line_id.day_9:
                        self.to_shift_ids = month_shift_line_id.day_9
                elif day_filter == 'day_10':
                    if month_shift_line_id.day_10:
                        self.to_shift_ids = month_shift_line_id.day_10
                elif day_filter == 'day_11':
                    if month_shift_line_id.day_11:
                        self.to_shift_ids = month_shift_line_id.day_11
                elif day_filter == 'day_12':
                    if month_shift_line_id.day_12:
                        self.to_shift_ids = month_shift_line_id.day_12
                elif day_filter == 'day_13':
                    if month_shift_line_id.day_13:
                        self.to_shift_ids = month_shift_line_id.day_13
                elif day_filter == 'day_14':
                    if month_shift_line_id.day_14:
                        self.to_shift_ids = month_shift_line_id.day_14
                elif day_filter == 'day_15':
                    if month_shift_line_id.day_15:
                        self.to_shift_ids = month_shift_line_id.day_15
                elif day_filter == 'day_16':
                    if month_shift_line_id.day_16:
                        self.to_shift_ids = month_shift_line_id.day_16
                elif day_filter == 'day_17':
                    if month_shift_line_id.day_17:
                        self.to_shift_ids = month_shift_line_id.day_17
                elif day_filter == 'day_18':
                    if month_shift_line_id.day_18:
                        self.to_shift_ids = month_shift_line_id.day_18
                elif day_filter == 'day_19':
                    if month_shift_line_id.day_19:
                        self.to_shift_ids = month_shift_line_id.day_19
                elif day_filter == 'day_20':
                    if month_shift_line_id.day_20:
                        self.to_shift_ids = month_shift_line_id.day_20
                elif day_filter == 'day_21':
                    if month_shift_line_id.day_21:
                        self.to_shift_ids = month_shift_line_id.day_21
                elif day_filter == 'day_22':
                    if month_shift_line_id.day_22:
                        self.to_shift_ids = month_shift_line_id.day_22
                elif day_filter == 'day_23':
                    if month_shift_line_id.day_23:
                        self.to_shift_ids = month_shift_line_id.day_23
                elif day_filter == 'day_24':
                    if month_shift_line_id.day_24:
                        self.to_shift_ids = month_shift_line_id.day_24
                elif day_filter == 'day_25':
                    if month_shift_line_id.day_25:
                        self.to_shift_ids = month_shift_line_id.day_25
                elif day_filter == 'day_26':
                    if month_shift_line_id.day_26:
                        self.to_shift_ids = month_shift_line_id.day_26
                elif day_filter == 'day_27':
                    if month_shift_line_id.day_27:
                        self.to_shift_ids = month_shift_line_id.day_27
                elif day_filter == 'day_28':
                    if month_shift_line_id.day_28:
                        self.to_shift_ids = month_shift_line_id.day_28
                elif day_filter == 'day_29':
                    if month_shift_line_id.day_29:
                        self.to_shift_ids = month_shift_line_id.day_29
                elif day_filter == 'day_30':
                    if month_shift_line_id.day_30:
                        self.to_shift_ids = month_shift_line_id.day_30
                elif day_filter == 'day_31':
                    if month_shift_line_id.day_31:
                        self.to_shift_ids = month_shift_line_id.day_31

    def action_draft(self):
        self.state = 'draft'

    def action_done(self):
        for rec in self:
            if rec.from_employee_id == self.to_employee_id:
                raise UserError(_('Same Employee Selected!'))
            if not rec.from_shift_ids:
                raise UserError(_('No Shift Selected!'))
            if self.to_shift_ids:
                for x,y in zip(self.from_shift_ids, self.to_shift_ids):
                    if x.id == y.id:
                        raise UserError(_('Can not Alter! Both Employee has same Shift!'))
            date_str = str(self.date)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            year = date_obj.year
            day = date_obj.day
            month_str = date_obj.strftime('%m')
            day_filter = 'day_' + str(day)
            month_shift_id = self.env['rostering.monthly.shift'].search([('month', '=', month_str),
                                                                         ('year', '=', year),
                                                                         ('department_id', '=', self.department_id.id)],
                                                                        limit=1)
            # from employee
            month_shift_line_id = self.env['rostering.monthly.shift.line'].search([('head_id', '=', month_shift_id.id),
                                                                                   ('employee_id', '=',
                                                                                    self.from_employee_id.id)],
                                                                                  limit=1)
            if not month_shift_line_id:
                raise UserError(_(self.from_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first!'))

            if day_filter == 'day_1':
                if month_shift_line_id.day_1:
                    month_shift_line_id.day_1 = None
            elif day_filter == 'day_2':
                if month_shift_line_id.day_2:
                    month_shift_line_id.day_2 = None
            elif day_filter == 'day_3':
                if month_shift_line_id.day_3:
                    month_shift_line_id.day_3 = None
            elif day_filter == 'day_4':
                if month_shift_line_id.day_4:
                    month_shift_line_id.day_4 = None
            elif day_filter == 'day_5':
                if month_shift_line_id.day_5:
                    month_shift_line_id.day_5 = None
            elif day_filter == 'day_6':
                if month_shift_line_id.day_6:
                    month_shift_line_id.day_6 = None
            elif day_filter == 'day_7':
                if month_shift_line_id.day_7:
                    month_shift_line_id.day_7 = None
            elif day_filter == 'day_8':
                if month_shift_line_id.day_8:
                    month_shift_line_id.day_8 = None
            elif day_filter == 'day_9':
                if month_shift_line_id.day_9:
                    month_shift_line_id.day_9 = None
            elif day_filter == 'day_10':
                if month_shift_line_id.day_10:
                    month_shift_line_id.day_10 = None
            elif day_filter == 'day_11':
                if month_shift_line_id.day_11:
                    month_shift_line_id.day_11 = None
            elif day_filter == 'day_12':
                if month_shift_line_id.day_12:
                    month_shift_line_id.day_12 = None
            elif day_filter == 'day_13':
                if month_shift_line_id.day_13:
                    month_shift_line_id.day_13 = None
            elif day_filter == 'day_14':
                if month_shift_line_id.day_14:
                    month_shift_line_id.day_14 = None
            elif day_filter == 'day_15':
                if month_shift_line_id.day_15:
                    month_shift_line_id.day_15 = None
            elif day_filter == 'day_16':
                if month_shift_line_id.day_16:
                    month_shift_line_id.day_16 = None
            elif day_filter == 'day_17':
                if month_shift_line_id.day_17:
                    month_shift_line_id.day_17 = None
            elif day_filter == 'day_18':
                if month_shift_line_id.day_18:
                    month_shift_line_id.day_18 = None
            elif day_filter == 'day_19':
                if month_shift_line_id.day_19:
                    month_shift_line_id.day_19 = None
            elif day_filter == 'day_20':
                if month_shift_line_id.day_20:
                    month_shift_line_id.day_20 = None
            elif day_filter == 'day_21':
                if month_shift_line_id.day_21:
                    month_shift_line_id.day_21 = None
            elif day_filter == 'day_22':
                if month_shift_line_id.day_22:
                    month_shift_line_id.day_22 = None
            elif day_filter == 'day_23':
                if month_shift_line_id.day_23:
                    month_shift_line_id.day_23 = None
            elif day_filter == 'day_24':
                if month_shift_line_id.day_24:
                    month_shift_line_id.day_24 = None
            elif day_filter == 'day_25':
                if month_shift_line_id.day_25:
                    month_shift_line_id.day_25 = None
            elif day_filter == 'day_26':
                if month_shift_line_id.day_26:
                    month_shift_line_id.day_26 = None
            elif day_filter == 'day_27':
                if month_shift_line_id.day_27:
                    month_shift_line_id.day_27 = None
            elif day_filter == 'day_28':
                if month_shift_line_id.day_28:
                    month_shift_line_id.day_28 = None
            elif day_filter == 'day_29':
                if month_shift_line_id.day_29:
                    month_shift_line_id.day_29 = None
            elif day_filter == 'day_30':
                if month_shift_line_id.day_30:
                    month_shift_line_id.day_30 = None
            elif day_filter == 'day_31':
                if month_shift_line_id.day_31:
                    month_shift_line_id.day_31 = None

            # To employee
            to_month_shift_line_id = self.env['rostering.monthly.shift.line'].search([('head_id', '=', month_shift_id.id),
                                                                                      ('employee_id', '=', self.to_employee_id.id)],
                                                                                       limit=1)
            if not to_month_shift_line_id:
                raise UserError(_(self.to_employee_id.name + '- This Employee has no Shift on This Date, Create a Shift first!'))

            if day_filter == 'day_1':
                to_month_shift_line_id.day_1 += self.from_shift_ids
            elif day_filter == 'day_2':
                to_month_shift_line_id.day_2 += self.from_shift_ids
            elif day_filter == 'day_3':
                to_month_shift_line_id.day_3 += self.from_shift_ids
            elif day_filter == 'day_4':
                to_month_shift_line_id.day_4 += self.from_shift_ids
            elif day_filter == 'day_5':
                to_month_shift_line_id.day_5 += self.from_shift_ids
            elif day_filter == 'day_6':
                to_month_shift_line_id.day_6 += self.from_shift_ids
            elif day_filter == 'day_7':
                to_month_shift_line_id.day_7 += self.from_shift_ids
            elif day_filter == 'day_8':
                to_month_shift_line_id.day_8 += self.from_shift_ids
            elif day_filter == 'day_9':
                to_month_shift_line_id.day_9 += self.from_shift_ids
            elif day_filter == 'day_10':
                to_month_shift_line_id.day_10 += self.from_shift_ids
            elif day_filter == 'day_11':
                to_month_shift_line_id.day_11 += self.from_shift_ids
            elif day_filter == 'day_12':
                to_month_shift_line_id.day_12 += self.from_shift_ids
            elif day_filter == 'day_13':
                to_month_shift_line_id.day_13 += self.from_shift_ids
            elif day_filter == 'day_14':
                to_month_shift_line_id.day_14 += self.from_shift_ids
            elif day_filter == 'day_15':
                to_month_shift_line_id.day_15 += self.from_shift_ids
            elif day_filter == 'day_16':
                to_month_shift_line_id.day_1 += self.from_shift_ids
            elif day_filter == 'day_17':
                to_month_shift_line_id.day_17 += self.from_shift_ids
            elif day_filter == 'day_18':
                to_month_shift_line_id.day_18 += self.from_shift_ids
            elif day_filter == 'day_19':
                to_month_shift_line_id.day_19 += self.from_shift_ids
            elif day_filter == 'day_20':
                to_month_shift_line_id.day_20 += self.from_shift_ids
            elif day_filter == 'day_21':
                to_month_shift_line_id.day_21 += self.from_shift_ids
            elif day_filter == 'day_22':
                to_month_shift_line_id.day_22 += self.from_shift_ids
            elif day_filter == 'day_23':
                to_month_shift_line_id.day_23 += self.from_shift_ids
            elif day_filter == 'day_24':
                to_month_shift_line_id.day_24 += self.from_shift_ids
            elif day_filter == 'day_25':
                to_month_shift_line_id.day_25 += self.from_shift_ids
            elif day_filter == 'day_26':
                to_month_shift_line_id.day_26 += self.from_shift_ids
            elif day_filter == 'day_27':
                to_month_shift_line_id.day_27 += self.from_shift_ids
            elif day_filter == 'day_28':
                to_month_shift_line_id.day_28 += self.from_shift_ids
            elif day_filter == 'day_29':
                to_month_shift_line_id.day_29 += self.from_shift_ids
            elif day_filter == 'day_30':
                to_month_shift_line_id.day_30 += self.from_shift_ids
            elif day_filter == 'day_31':
                to_month_shift_line_id.day_31 += self.from_shift_ids

            rec.state = 'done'
            # if rec.code == 'New':
            #     rec.code = self.env['ir.sequence'].get('stock_unrealized_profit_loss_code')

    def action_cancel(self):
        self.state = 'cancel'

