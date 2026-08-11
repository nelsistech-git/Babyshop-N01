# -*- coding:utf-8 -*-
from datetime import date, datetime, time
from collections import defaultdict
from odoo import api, fields, models
from odoo.tools import date_utils

import pytz


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    
    @api.model
    def __def_resource_calendar(self):
        resource_id = self.env['resource.calendar'].search([('is_default', '=', True)], order="id asc", limit=1)
        if resource_id:
            return resource_id.id
        else:
            return self.env.company.resource_calendar_id.id

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours', copy=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", default=lambda self: self.__def_resource_calendar())

    @api.model
    def __def_structure_type(self):
        structure_id = self.env['hr.payroll.structure.type'].search([('name', '=', 'Regular Pay')], order="id asc", limit=1)
        if structure_id:
            return structure_id.id
        else:
            return None

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", default=lambda self: self.__def_structure_type())

    @api.model
    def __def_structure(self):
        structure_id = self.env['hr.payroll.structure'].search([('code', '=', 'BASE')], order="id asc", limit=1)
        if structure_id:
            return structure_id.id
        else:
            return None
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', default=lambda self: self.__def_structure())

    bonus_struct_id = fields.Many2one('hr.payroll.structure', string='Bonus Structure')
    schedule_pay = fields.Selection(related='structure_type_id.default_struct_id.schedule_pay', depends=())
    # resource_calendar_id = fields.Many2one(required=True, default=lambda self: self.env.company.resource_calendar_id,
    #                                        help="Employee's working schedule.")
    hours_per_week = fields.Float(related='resource_calendar_id.hours_per_week')
    full_time_required_hours = fields.Float(related='resource_calendar_id.full_time_required_hours')
    is_fulltime = fields.Boolean(related='resource_calendar_id.is_fulltime')
    wage_type = fields.Selection(related='structure_type_id.wage_type')
    # hourly_wage = fields.Monetary('Hourly Wage', digits=(16, 2), default=0, required=True, tracking=True, help="Employee's hourly gross wage.")

    date_generated_from = fields.Datetime(string='Generated From', readonly=True, required=True,
                                          default=lambda self: datetime.now().replace(hour=0, minute=0, second=0),
                                          copy=False)
    date_generated_to = fields.Datetime(string='Generated To', readonly=True, required=True,
                                        default=lambda self: datetime.now().replace(hour=0, minute=0, second=0),
                                        copy=False)

    company_country_id = fields.Many2one('res.country', string="Company country", related='company_id.country_id',
                                         readonly=True)

    hra = fields.Monetary(string='House Rent Allowance', help="House rent allowance.")
    travel_allowance = fields.Monetary(string="Conveyance Allowance", help="Conveyance Allowance")
    da = fields.Monetary(string="Dearness Allowance", help="Dearness Allowance")
    meal_allowance = fields.Monetary(string="Meal Allowance", help="Meal/Food allowance")
    medical_allowance = fields.Monetary(string="Medical Allowance", help="Medical allowance")
    mobile_allowance = fields.Monetary(string="Mobile Allowance", help="Mobile allowance")
    car_allowance = fields.Monetary(string="Car Allowance", help="Car allowance")
    lfa_allowance = fields.Monetary(string="LFA Allowance", default=0, help="Leave Fare Assistance")
    salary_bonus_allowance = fields.Monetary(string="Salary Bonus Allowance", default=0, help="Salary Bonus")
    other_allowance = fields.Monetary(string="Other/Special Allowance", help="Other allowances")
    is_tiffin_alw_allowed = fields.Boolean(string="Is Tiffin Allowed?", help="Tiffin Allowance allowed or not.")
    tiffin_alw_type = fields.Selection([
        ('0', 'Daily'),
        ('1', 'Monthly'),
    ], string="Tiffin Daily/Monthy?", default="0")
    tiffin_allowance = fields.Monetary(string="Tiffin Allowance", help="Tiffin allowances")

    gross_salary = fields.Float(string="Gross Salary")
    wage = fields.Monetary('Basic', required=True, help="Employee's monthly gross wage.")
    total_allowance = fields.Float(string="Total Allowance", compute='_compute_total_allowance')

    pf_deduction = fields.Monetary(string="PF Deduction", help="Provident Fund Deduction")
    tds_deduction = fields.Monetary(string="TDS Deduction", help="TDS Deduction")
    stamp_deduction = fields.Monetary(string="Stamp Fee", help="Stamp Fee")
    total_deduction = fields.Float(string="Total Deduction", compute='_compute_total_deduction')
    net_salary = fields.Float(string="Net Salary", compute='_compute_net_salary')
    company_pf_contribution = fields.Monetary(string="Company PF Contribution", help="Company PF Contribution")
    profit = fields.Monetary(string="Profit", help="Profit")
    special_house_rent = fields.Monetary(string="Special House Rent", help="Special House Rent")
    special_incentive = fields.Monetary(string="Special Incentive", help="Special Incentive")
    profit_sharing = fields.Monetary(string="Profit Sharing", help="Profit Sharing")
    festival_bonus = fields.Monetary(string="Festival Bonus", help="Festival Bonus")
    special_bonus = fields.Monetary(string="Special Bonus", help="Special Bonus")
    is_att_bonus_allowed = fields.Boolean(string="Is Attendance Bonus Allowed?", help="Attendance Bonus allowed or not.")
    att_bonus_rate = fields.Monetary(string="Attendance Bonus Rate", help="Attendance Bonus Rate")

    daily_allowance = fields.Float(string="Daily Allowance", help="Daily Allowance")

    is_ot_allowed = fields.Boolean(string="Is OT Allowed?",
                                          help="OT allowed or not.") #for IMBD
    ot_day_count = fields.Float(string="Overtime Day Count", help="Overtime Day Count", default=26.00)
    ot_daily_allowance = fields.Float(string="Daily Overtime Allowance", help="Daily Overtime Allowance")
    conveyance_rate = fields.Float(string="Conveyance Rate", help="Conveyance Rate")
    ot_daily_salary = fields.Float(string="OT Daily Salary", compute="_compute_ot_daily_salary",
                                   help="Daily Overtime Salary")
    ot_type = fields.Selection([
                                ('daily', 'Daily'),
                                ('hourly', 'Hourly'),
                            ], string="OT Type", default="daily")
    ot_hourly_rate = fields.Float(string="OT Hourly Rate", help="Overtime Hourly Rate")

    pf_value = fields.Float(string="PF Value (Max)", help="result = (contract.pf_deduction*-1 or 0) if (contract.pf_deduction <= contract.pf_value or contract.pf_value == 0) else (2000*-1)")
    disbursement_type = fields.Selection([
                                        ('bank', 'Bank'),
                                        ('cash', 'Cash'),
                                        ('bank_cash', 'Bank & Cash')
                                    ], string="Payment Type", default="cash")
    s_bank_name = fields.Many2one('hr.bank', string="Salary Bank Name", help="Salary A/C Bank Name",
                                  related="employee_id.s_bank_name")
    s_bank_account_no = fields.Char(string='Salary Account No', help='Salary Account No',
                                    related="employee_id.s_bank_account_no")

    bank_account_id = fields.Many2one('account.account', string="Bank Account (CR)")
    cash_account_id = fields.Many2one('account.account', string="Cash Account (CR)")
    is_pf_allowed = fields.Boolean(string="PF Apply?", default=False)

    @api.onchange('employee_id')
    def change_employee_id_disburseemnt_type(self):
        if self.employee_id and self.employee_id.disbursement_type:
            self.disbursement_type = self.employee_id.disbursement_type

    @api.onchange('disbursement_type')
    def _onchange_disbursement_type(self):
        if self.disbursement_type == 'cash':
            return {'value': {'bank_account_id': None}}
        elif self.disbursement_type == 'bank':
            return {'value': {'cash_account_id': None}}
        else:
            return {'value': {'cash_account_id': None, 'bank_account_id': None}}

    # @api.onchange('department_id')
    # def _onchange_department(self):
    #     if self.department_id:
    #         self.job_id = ""

    @api.onchange('gross_salary', 'wage')
    def set_gross_distribution(self):
        basic_value = 0
        hra_value = 0
        da_value = 0
        travel_value = 0
        travel_on_basic_value = 0
        meal_value = 0
        medical_value = 0
        pf_value = 0
        company_pf_value = 0
        festival_bonus_value = 0
        
        medical_fixed_value = 0
        basic_gmv_value = 0
        hra_on_basic_value = 0
        pf_on_basic_value =0
        medical_on_basic_value = 0
        food_on_basic_value = 0
        conveyance_value = 0
        attendance_fixed_bonus_value = 0
        food_on_fixed_value = 0
        attendance_fixed_tiffin_value = 0

        basic_row = self.env['hr.contract.particular.settings'].search([])
        for rec in basic_row:
            if rec.name == 'basic' and (rec.value > 0 and rec.value <= 100):
                basic_value = rec.value
            elif rec.name == 'hra' and (rec.value > 0 and rec.value <= 100):
                hra_value = rec.value
            elif rec.name == 'da' and (rec.value > 0 and rec.value <= 100):
                da_value = rec.value
            elif rec.name == 'travel' and (rec.value > 0 and rec.value <= 100):
                travel_value = rec.value
            elif rec.name == 'travel_on_basic' and (rec.value > 0 and rec.value <= 100):
                travel_on_basic_value = rec.value
            elif rec.name == 'meal' and (rec.value > 0 and rec.value <= 100):
                meal_value = rec.value
            elif rec.name == 'medical' and (rec.value > 0 and rec.value <= 100):
                medical_value = rec.value
            elif rec.name == 'pf' and (rec.value > 0 and rec.value <= 100):
                pf_value = rec.value
            elif rec.name == 'company_pf' and (rec.value > 0 and rec.value <= 100):
                company_pf_value = rec.value
            elif rec.name == 'festival_bonus' and (rec.value > 0 and rec.value <= 100):
                festival_bonus_value = rec.value
            elif rec.name == 'medical_fixed' and rec.value > 0:
                medical_fixed_value = rec.value
            elif rec.name == 'basic_gmv' and rec.value > 0:
                basic_gmv_value = rec.value
            elif rec.name == 'hra_on_basic' and (rec.value > 0 and rec.value <= 100):
                hra_on_basic_value = rec.value
            elif rec.name == 'medical_on_basic' and (rec.value > 0 and rec.value <= 100):
                medical_on_basic_value = rec.value
            elif rec.name == 'pf_on_basic' and (rec.value > 0 and rec.value <= 100):
                pf_on_basic_value = rec.value
            elif rec.name == 'food_on_basic' and (rec.value > 0 and rec.value <= 100):
                food_on_basic_value = rec.value
            elif rec.name == 'food_on_fixed' and (rec.value > 0 and rec.value <= 100):
                food_on_fixed_value = rec.value
            elif rec.name == 'attendance_fixed_bonus' and (rec.value > 0 and rec.value <= 100):
                attendance_fixed_bonus_value = rec.value
            elif rec.name == 'attendance_fixed_tiffin' and (rec.value > 0 and rec.value <= 100):
                attendance_fixed_tiffin_value = rec.value


        #first priority

        #-------Basic
        if basic_value:
            self.wage = round(self.gross_salary * (basic_value / 100), 2)
        elif basic_gmv_value:
            self.wage = round((self.gross_salary - self.medical_allowance) / basic_gmv_value, 2)

        #--------House Rent
        if hra_value:
            self.hra = round(self.gross_salary * (hra_value / 100), 2)
        elif hra_on_basic_value:
            self.hra = round(self.wage * (hra_on_basic_value / 100), 2)

        #--------------da
        if da_value:
            self.da = round(self.gross_salary * (da_value / 100), 2)

        #----------convence
        if travel_value:
            self.travel_allowance = round(self.gross_salary * (travel_value / 100), 2)
        elif travel_on_basic_value:
            self.travel_allowance = round(self.wage * (travel_on_basic_value / 100), 2)

        #----------meal
        if meal_value:
            self.meal_allowance = round(self.gross_salary * (meal_value / 100), 2)
        elif food_on_basic_value:
            self.meal_allowance = round(self.wage * (food_on_basic_value / 100), 2)
        elif food_on_fixed_value:
            self.meal_allowance = round(food_on_fixed_value, 2)

        # --------- Medical
        if medical_fixed_value:
            self.medical_allowance = medical_fixed_value
        elif medical_value:
            self.medical_allowance = round(self.gross_salary * (medical_value / 100), 2)
        elif medical_on_basic_value:
            self.medical_allowance = round(self.wage * (medical_on_basic_value / 100), 2)

        #--------------
        if pf_value:
            self.pf_deduction = round(self.gross_salary * (pf_value / 100), 2)
        elif pf_on_basic_value:
            self.pf_deduction = round(self.wage * (pf_on_basic_value / 100), 2)

        #-----------
        if company_pf_value:
            self.company_pf_contribution = round(self.pf_deduction * (company_pf_value / 100), 2)
        if festival_bonus_value:
            self.festival_bonus = round(self.gross_salary * (festival_bonus_value / 100), 2)

        if attendance_fixed_bonus_value:
            self.att_bonus_rate = round(attendance_fixed_bonus_value, 2)
        if attendance_fixed_tiffin_value:
            self.tiffin_allowance = round(attendance_fixed_tiffin_value, 2)

        self.other_allowance = self.gross_salary - (
                self.wage + self.hra + self.da + self.travel_allowance + self.lfa_allowance + self.salary_bonus_allowance + self.meal_allowance + self.medical_allowance + self.mobile_allowance + self.car_allowance)  #

    def set_gross_distribution_fnc(self):
        basic_value = 0
        hra_value = 0
        da_value = 0
        travel_value = 0
        travel_on_basic_value = 0
        meal_value = 0
        medical_value = 0
        pf_value = 0
        company_pf_value = 0
        festival_bonus_value = 0

        medical_fixed_value = 0
        basic_gmv_value = 0
        hra_on_basic_value = 0
        pf_on_basic_value = 0
        medical_on_basic_value = 0
        food_on_basic_value = 0
        conveyance_value = 0
        attendance_fixed_bonus_value = 0
        food_on_fixed_value = 0
        attendance_fixed_tiffin_value = 0

        basic_row = self.env['hr.contract.particular.settings'].search([])
        for rec in basic_row:
            if rec.name == 'basic' and (rec.value > 0 and rec.value <= 100):
                basic_value = rec.value
            elif rec.name == 'hra' and (rec.value > 0 and rec.value <= 100):
                hra_value = rec.value
            elif rec.name == 'da' and (rec.value > 0 and rec.value <= 100):
                da_value = rec.value
            elif rec.name == 'travel' and (rec.value > 0 and rec.value <= 100):
                travel_value = rec.value
            elif rec.name == 'travel_on_basic' and (rec.value > 0 and rec.value <= 100):
                travel_on_basic_value = rec.value
            elif rec.name == 'meal' and (rec.value > 0 and rec.value <= 100):
                meal_value = rec.value
            elif rec.name == 'medical' and (rec.value > 0 and rec.value <= 100):
                medical_value = rec.value
            elif rec.name == 'pf' and (rec.value > 0 and rec.value <= 100):
                pf_value = rec.value
            elif rec.name == 'company_pf' and (rec.value > 0 and rec.value <= 100):
                company_pf_value = rec.value
            elif rec.name == 'festival_bonus' and (rec.value > 0 and rec.value <= 100):
                festival_bonus_value = rec.value
            elif rec.name == 'medical_fixed' and rec.value > 0:
                medical_fixed_value = rec.value
            elif rec.name == 'basic_gmv' and rec.value > 0:
                basic_gmv_value = rec.value
            elif rec.name == 'hra_on_basic' and (rec.value > 0 and rec.value <= 100):
                hra_on_basic_value = rec.value
            elif rec.name == 'medical_on_basic' and (rec.value > 0 and rec.value <= 100):
                medical_on_basic_value = rec.value
            elif rec.name == 'pf_on_basic' and (rec.value > 0 and rec.value <= 100):
                pf_on_basic_value = rec.value
            elif rec.name == 'food_on_basic' and (rec.value > 0 and rec.value <= 100):
                food_on_basic_value = rec.value
            elif rec.name == 'food_on_fixed' and (rec.value > 0 and rec.value <= 100):
                food_on_fixed_value = rec.value
            elif rec.name == 'attendance_fixed_bonus' and (rec.value > 0 and rec.value <= 100):
                attendance_fixed_bonus_value = rec.value
            elif rec.name == 'attendance_fixed_tiffin' and (rec.value > 0 and rec.value <= 100):
                attendance_fixed_tiffin_value = rec.value

        # first priority

        # -------Basic
        if basic_value:
            self.wage = round(self.gross_salary * (basic_value / 100), 2)
        elif basic_gmv_value:
            self.wage = round((self.gross_salary - self.medical_allowance) / basic_gmv_value, 2)

        # --------House Rent
        if hra_value:
            self.hra = round(self.gross_salary * (hra_value / 100), 2)
        elif hra_on_basic_value:
            self.hra = round(self.wage * (hra_on_basic_value / 100), 2)

        # --------------da
        if da_value:
            self.da = round(self.gross_salary * (da_value / 100), 2)

        # ----------convence
        if travel_value:
            self.travel_allowance = round(self.gross_salary * (travel_value / 100), 2)
        elif travel_on_basic_value:
            self.travel_allowance = round(self.wage * (travel_on_basic_value / 100), 2)

        # ----------meal
        if meal_value:
            self.meal_allowance = round(self.gross_salary * (meal_value / 100), 2)
        elif food_on_basic_value:
            self.meal_allowance = round(self.wage * (food_on_basic_value / 100), 2)
        elif food_on_fixed_value:
            self.meal_allowance = round(food_on_fixed_value, 2)

        # --------- Medical
        if medical_fixed_value:
            self.medical_allowance = medical_fixed_value
        elif medical_value:
            self.medical_allowance = round(self.gross_salary * (medical_value / 100), 2)
        elif medical_on_basic_value:
            self.medical_allowance = round(self.wage * (medical_on_basic_value / 100), 2)

        # --------------
        if pf_value:
            self.pf_deduction = round(self.gross_salary * (pf_value / 100), 2)
        elif pf_on_basic_value:
            self.pf_deduction = round(self.wage * (pf_on_basic_value / 100), 2)

        # -----------
        if company_pf_value:
            self.company_pf_contribution = round(self.pf_deduction * (company_pf_value / 100), 2)
        if festival_bonus_value:
            self.festival_bonus = round(self.gross_salary * (festival_bonus_value / 100), 2)

        if attendance_fixed_bonus_value:
            self.att_bonus_rate = round(attendance_fixed_bonus_value, 2)
        if attendance_fixed_tiffin_value:
            self.tiffin_allowance = round(attendance_fixed_tiffin_value, 2)

        self.other_allowance = self.gross_salary - (
                self.wage + self.hra + self.da + self.travel_allowance + self.lfa_allowance + self.salary_bonus_allowance + self.meal_allowance + self.medical_allowance + self.mobile_allowance + self.car_allowance)  #

    @api.depends('ot_day_count', 'gross_salary')
    def _compute_ot_daily_salary(self):
        for rec in self:
            try:
                rec.ot_daily_salary = rec.gross_salary / rec.ot_day_count
            except:
                rec.ot_daily_salary = 0

    # @api.onchange('is_att_bonus_allowed', 'att_bonus_rate')
    # def _onchange_is_att_bonus_allowed(self):
    #     if not self.is_att_bonus_allowed:
    #         self.att_bonus_rate = 0

    # @api.onchange('is_tiffin_alw_allowed', 'tiffin_allowance')
    # def _onchange_is_tiffin_alw_allowed(self):
    #     if not self.is_tiffin_alw_allowed:
    #         self.tiffin_allowance = 0

    @api.depends('wage', 'hra', 'da', 'travel_allowance', 'meal_allowance', 'medical_allowance', 'other_allowance',
                 'mobile_allowance', 'car_allowance', 'lfa_allowance', 'salary_bonus_allowance')
    def _compute_total_allowance(self):
        for rec in self:
            rec.total_allowance = (
                    rec.wage + rec.hra + rec.da + rec.travel_allowance + rec.meal_allowance + rec.medical_allowance + rec.other_allowance + rec.mobile_allowance + rec.car_allowance + rec.lfa_allowance + rec.salary_bonus_allowance)

    @api.depends('pf_deduction', 'tds_deduction', 'stamp_deduction')
    def _compute_total_deduction(self):
        for rec in self:
            rec.total_deduction = (rec.pf_deduction + rec.tds_deduction + rec.stamp_deduction)

    @api.depends('total_allowance',
                 'total_deduction')  # ,'special_house_rent', 'special_incentive', 'profit_sharing', 'festival_bonus', 'special_bonus'
    def _compute_net_salary(self):
        for rec in self:
            rec.net_salary = (
                        rec.total_allowance - rec.total_deduction)  # + rec.special_house_rent + rec.special_incentive + rec.profit_sharing + rec.festival_bonus + rec.special_bonus

    @api.constrains('date_start', 'date_end', 'state')
    def _check_contracts(self):
        self._get_leaves()._check_contracts()

    @api.onchange('structure_type_id')
    def _onchange_structure_type_id(self):
        if self.structure_type_id.default_resource_calendar_id:
            self.resource_calendar_id = self.structure_type_id.default_resource_calendar_id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            structure_types = self.env['hr.payroll.structure.type'].search([
                '|',
                ('country_id', '=', self.company_id.country_id.id),
                ('country_id', '=', False)])
            if structure_types:
                self.structure_type_id = structure_types[0]
            elif self.structure_type_id not in structure_types:
                self.structure_type_id = False

    def _get_leaves(self):
        return self.env['hr.leave'].search([
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('date_from', '<=', max([end or date.max for end in self.mapped('date_end')])),
            ('date_to', '>=', min(self.mapped('date_start'))),
        ])
    #custom billal
    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first,
                 then first level children and so on) and without duplicata
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        
        all_struc_list = []
        if self.struct_id:
            all_struc_list.append(self.struct_id.id)
        if self.bonus_struct_id:
            all_struc_list.append(self.bonus_struct_id.id)
            
        return all_struc_list
        
    def _get_work_entries_values(self, date_start, date_stop):
        """
        Generate a work_entries list between date_start and date_stop for one contract.
        :return: list of dictionnary.
        """
        default_work_entry_type = self.structure_type_id.default_work_entry_type_id
        vals_list = []

        for contract in self:
            contract_vals = []
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            tz = pytz.timezone(calendar.tz)

            attendances = calendar._work_intervals_batch(
                pytz.utc.localize(date_start) if not date_start.tzinfo else date_start,
                pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop,
                resources=resource, tz=tz
            )
            # Attendances
            for interval in attendances:
                #work_entry_type_id = interval[2].mapped('work_entry_type_id')[:1] or default_work_entry_type
                work_entry_type_id = default_work_entry_type
                # All benefits generated here are using datetimes converted from the employee's timezone
                day_start_native = date_start.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
                day_end_native = date_stop.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)

                contract_vals += [{
                    'name': "%s: %s" % (work_entry_type_id.name, employee.name),
                    'date_start': day_start_native, #interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                    'date_stop': day_end_native, #interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                    'work_entry_type_id': work_entry_type_id.id,
                    'employee_id': employee.id,
                    'contract_id': contract.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                }]

            # Leaves
            leaves = self.env['resource.calendar.leaves'].sudo().search([
                ('resource_id', 'in', [False, resource.id]),
                ('calendar_id', '=', calendar.id),
                ('date_from', '<', date_stop),
                ('date_to', '>', date_start)
            ])

            for leave in leaves:
                start = max(leave.date_from, datetime.combine(contract.date_start, datetime.min.time()))
                end = min(leave.date_to, datetime.combine(contract.date_end or date.max, datetime.max.time()))
                if leave.holiday_id:
                    work_entry_type = leave.holiday_id.holiday_status_id.work_entry_type_id
                else:
                    work_entry_type = leave.mapped('work_entry_type_id')
                contract_vals += [{
                    'name': "%s%s" % (work_entry_type.name + ": " if work_entry_type else "", employee.name),
                    'date_start': start,
                    'date_stop': end,
                    'work_entry_type_id': work_entry_type.id,
                    'employee_id': employee.id,
                    'leave_id': leave.holiday_id and leave.holiday_id.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                    'contract_id': contract.id,
                }]

            # If we generate work_entries which exceeds date_start or date_stop, we change boundaries on contract
            if contract_vals:
                date_stop_max = max([x['date_stop'] for x in contract_vals])
                if date_stop_max > contract.date_generated_to:
                    contract.date_generated_to = date_stop_max

                date_start_min = min([x['date_start'] for x in contract_vals])
                if date_start_min < contract.date_generated_from:
                    contract.date_generated_from = date_start_min

            vals_list += contract_vals

        return vals_list

    def _generate_work_entries(self, date_start, date_stop):
        vals_list = []

        date_start = fields.Datetime.to_datetime(date_start)
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())

        for contract in self:
            # For each contract, we found each interval we must generate
            contract_start = fields.Datetime.to_datetime(contract.date_start)
            contract_stop = datetime.combine(fields.Datetime.to_datetime(contract.date_end or datetime.max.date()),
                                             datetime.max.time())
            last_generated_from = min(contract.date_generated_from, contract_stop)
            date_start_work_entries = max(date_start, contract_start)

            if last_generated_from > date_start_work_entries:
                contract.date_generated_from = date_start_work_entries
                vals_list.extend(contract._get_work_entries_values(date_start_work_entries, last_generated_from))

            last_generated_to = max(contract.date_generated_to, contract_start)
            date_stop_work_entries = min(date_stop, contract_stop)
            if last_generated_to < date_stop_work_entries:
                contract.date_generated_to = date_stop_work_entries
                vals_list.extend(contract._get_work_entries_values(last_generated_to, date_stop_work_entries))

        if not vals_list:
            return self.env['hr.work.entry']

        return self.env['hr.work.entry'].create(vals_list)

    def _index_contracts(self):
        action = self.env.ref('hr_payroll.action_hr_payroll_index').read()[0]
        action['context'] = repr(self.env.context)
        return action

    def _get_work_hours(self, date_from, date_to):
        """
        Returns the amount (expressed in hours) of work
        for a contract between two dates.
        If called on multiple contracts, sum work amounts of each contract.
        :param date_from: The start date
        :param date_to: The end date
        :returns: a dictionary {work_entry_id: hours_1, work_entry_2: hours_2}
        """

        generated_date_max = min(fields.Date.to_date(date_to), date_utils.end_of(fields.Date.today(), 'month'))
        self._generate_work_entries(date_from, generated_date_max)
        date_from = datetime.combine(date_from, datetime.min.time())
        date_to = datetime.combine(date_to, datetime.max.time())
        work_data = defaultdict(int)

        # First, found work entry that didn't exceed interval.
        work_entries = self.env['hr.work.entry'].read_group(
            [
                ('state', 'in', ['validated', 'draft']),
                ('date_start', '>=', date_from),
                ('date_stop', '<=', date_to),
                ('contract_id', 'in', self.ids),
            ],
            ['hours:sum(duration)'],
            ['work_entry_type_id']
        )
        work_data.update(
            {data['work_entry_type_id'][0] if data['work_entry_type_id'] else False: data['hours'] for data in
             work_entries})

        # Second, found work entry that exceed interval and compute right duration.
        work_entries = self.env['hr.work.entry'].search(
            [
                '&', '&',
                ('state', 'in', ['validated', 'draft']),
                ('contract_id', 'in', self.ids),
                '|', '|', '&', '&',
                ('date_start', '>=', date_from),
                ('date_start', '<', date_to),
                ('date_stop', '>', date_to),
                '&', '&',
                ('date_start', '<', date_from),
                ('date_stop', '<=', date_to),
                ('date_stop', '>', date_from),
                '&',
                ('date_start', '<', date_from),
                ('date_stop', '>', date_to),
            ]
        )

        for work_entry in work_entries:
            date_start = max(date_from, work_entry.date_start)
            date_stop = min(date_to, work_entry.date_stop)
            if work_entry.work_entry_type_id.is_leave:
                contract = work_entry.contract_id
                calendar = contract.resource_calendar_id
                contract_data = contract.employee_id._get_work_days_data(date_start, date_stop, compute_leaves=False,
                                                                         calendar=calendar)

                work_data[work_entry.work_entry_type_id.id] += contract_data.get('hours', 0)
            else:
                dt = date_stop - date_start
                work_data[work_entry.work_entry_type_id.id] += dt.days * 24 + dt.seconds / 3600  # Number of hours
        return work_data

    def _remove_work_entries(self):
        ''' Remove all work_entries that are outside contract period (function used after writing new start or/and end date) '''
        all_we_to_unlink = self.env['hr.work.entry']
        for contract in self:
            date_start = fields.Datetime.to_datetime(contract.date_start)
            if contract.date_generated_from < date_start:
                we_to_remove = self.env['hr.work.entry'].search(
                    [('date_stop', '<=', date_start), ('contract_id', '=', contract.id)])
                if we_to_remove:
                    contract.date_generated_from = date_start
                    all_we_to_unlink |= we_to_remove
            if not contract.date_end:
                continue
            date_end = datetime.combine(contract.date_end, datetime.max.time())
            if contract.date_generated_to > date_end:
                we_to_remove = self.env['hr.work.entry'].search(
                    [('date_start', '>=', date_end), ('contract_id', '=', contract.id)])
                if we_to_remove:
                    contract.date_generated_to = date_end
                    all_we_to_unlink |= we_to_remove
        all_we_to_unlink.unlink()

    def write(self, vals):
        result = super(HrContract, self).write(vals)
        if vals.get('date_end') or vals.get('date_start'):
            self._remove_work_entries()

        emp_flag = self.env.context.get("emp_flag") or False
        if emp_flag == False:
            if vals.get('disbursement_type'):
                self.employee_id.with_context(contract_flag=True).write({'disbursement_type': self.disbursement_type})

        return result
