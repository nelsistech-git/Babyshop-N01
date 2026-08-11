from odoo import models, fields, api
import datetime
from datetime import datetime
from odoo.addons.helper import validator


class RosteringMonthlyShift(models.Model):
    _name = "rostering.monthly.shift"
    _description = "Rostering Monthly Shift"
    _rec_name = 'month'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    # employee_id = fields.Many2many('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department')
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
    ], string='Month', required=True)

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            # start_year = int(str(company.start_date).split("-")[0])
            start_year = company.start_date.year
            if company.display_year:
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    # shift_id = fields.Many2many('rostering.shift.settings')
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('rostering.monthly.shift.line', 'head_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approve'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=24, default='draft')
    
    @api.constrains('year', 'department_id', 'month')
    def _check_unique_month_year(self):
        for rec in self:
            msg = 'Month  "%s"' % (rec.month)
            envobj = self.env['rostering.monthly.shift']
            conditionlist = [('year', '=', rec.year),('department_id', '=', rec.department_id.id), ('month', '=', rec.month)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'
            # if rec.code == 'New':
            #     rec.code = self.env['ir.sequence'].get('stock_unrealized_profit_loss_code')

    def action_cancel(self):
        self.state = 'cancel'


class RosteringMonthlyShiftLine(models.Model):
    _name = "rostering.monthly.shift.line"
    _description = "Rostering Monthly Shift Line"

    head_id = fields.Many2one('rostering.monthly.shift', ondelete='cascade')
    department_id = fields.Many2one('hr.department', string='Department', related='head_id.department_id')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    # shift_id = fields.Many2many('rostering.shift.settings')

    day_1 = fields.Many2many('rostering.shift.settings', 'relation_table_one', 'col1', 'col2', string="Day 1")
    day_2 = fields.Many2many('rostering.shift.settings', 'relation_table_two', 'col1', 'col2', string="Day 2")
    day_3 = fields.Many2many('rostering.shift.settings','relation_table_three', 'col1', 'col2', string='Day 3')
    day_4 = fields.Many2many('rostering.shift.settings','relation_table_4', 'col1', 'col2', string='Day 4')
    day_5 = fields.Many2many('rostering.shift.settings','relation_table_5', 'col1', 'col2', string='Day 5')
    day_6 = fields.Many2many('rostering.shift.settings','relation_table_6', 'col1', 'col2', string='Day 6')
    day_7 = fields.Many2many('rostering.shift.settings','relation_table_7', 'col1', 'col2', string='Day 7')
    day_8 = fields.Many2many('rostering.shift.settings','relation_table_8', 'col1', 'col2', string='Day 8')
    day_9 = fields.Many2many('rostering.shift.settings','relation_table_9', 'col1', 'col2', string='Day 9')
    day_10 = fields.Many2many('rostering.shift.settings','relation_table_10', 'col1', 'col2', string='Day 10')
    day_11 = fields.Many2many('rostering.shift.settings','relation_table_11', 'col1', 'col2', string='Day 11')
    day_12 = fields.Many2many('rostering.shift.settings','relation_table_12', 'col1', 'col2', string='Day 12')
    day_13 = fields.Many2many('rostering.shift.settings','relation_table_13e', 'col1', 'col2', string='Day 13')
    day_14 = fields.Many2many('rostering.shift.settings','relation_table_14', 'col1', 'col2', string='Day 14')
    day_15 = fields.Many2many('rostering.shift.settings','relation_table_15', 'col1', 'col2', string='Day 15')
    day_16 = fields.Many2many('rostering.shift.settings','relation_table_16e', 'col1', 'col2', string='Day 16')
    day_17 = fields.Many2many('rostering.shift.settings','relation_table_17', 'col1', 'col2', string='Day 17')
    day_18 = fields.Many2many('rostering.shift.settings','relation_table_18', 'col1', 'col2', string='Day 18')
    day_19 = fields.Many2many('rostering.shift.settings','relation_table_19e', 'col1', 'col2', string='Day 19')
    day_20 = fields.Many2many('rostering.shift.settings','relation_table_20', 'col1', 'col2', string='Day 20')
    day_21 = fields.Many2many('rostering.shift.settings','relation_table_21', 'col1', 'col2', string='Day 21')
    day_22 = fields.Many2many('rostering.shift.settings','relation_table_22', 'col1', 'col2', string='Day 22')
    day_23 = fields.Many2many('rostering.shift.settings','relation_table_23', 'col1', 'col2', string='Day 23')
    day_24 = fields.Many2many('rostering.shift.settings','relation_table_24', 'col1', 'col2', string='Day 24')
    day_25 = fields.Many2many('rostering.shift.settings','relation_table_25', 'col1', 'col2', string='Day 25')
    day_26 = fields.Many2many('rostering.shift.settings','relation_table_26', 'col1', 'col2', string='Day 26')
    day_27 = fields.Many2many('rostering.shift.settings','relation_table_27', 'col1', 'col2', string='Day 27')
    day_28 = fields.Many2many('rostering.shift.settings','relation_table_28', 'col1', 'col2', string='Day 28')
    day_29 = fields.Many2many('rostering.shift.settings','relation_table_29', 'col1', 'col2', string='Day 29')
    day_30 = fields.Many2many('rostering.shift.settings','relation_table_30', 'col1', 'col2', string='Day 30')
    day_31 = fields.Many2many('rostering.shift.settings','relation_table_31', 'col1', 'col2', string='Day 31')

    @api.onchange('department_id')
    def onchange_department_id(self):
        if self.department_id:
            return {'domain': {'employee_id': [('department_id', '=', self.department_id.id), ('active', '=', True)]}}
        else:
            return {'domain': {'employee_id': [('active', '=', True)]}}
