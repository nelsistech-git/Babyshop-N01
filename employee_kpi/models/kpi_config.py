from odoo import models, fields, api
from odoo.exceptions import UserError


class KpiConfig(models.Model):
    _name = 'kpi.config'
    _description = 'KPI Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id, date desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New'
    )
    active = fields.Boolean(default=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True
    )
    staff_id = fields.Char(string='Staff ID', readonly=True)
    designation = fields.Char(string='Designation', readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True
    )

    date = fields.Date(
        string='Effective Date',
        default=fields.Date.today
    )

    # পুরনো field দুটো রেখে দিলাম (database safe)
    date_from = fields.Date(string='Date From')
    date_to   = fields.Date(string='Date To')

    task_line_ids = fields.One2many(
        'kpi.config.task', 'kpi_config_id', string='KPI Tasks'
    )

    # L1-L5 Rating Scale
    l1_min       = fields.Float(string='L1 Min (%)', default=0)
    l1_max       = fields.Float(string='L1 Max (%)', default=59)
    l1_label     = fields.Char(string='L1 Label', default='Unsatisfactory')
    l1_incentive = fields.Float(string='L1 Incentive (%)', default=0)

    l2_min       = fields.Float(string='L2 Min (%)', default=60)
    l2_max       = fields.Float(string='L2 Max (%)', default=69)
    l2_label     = fields.Char(string='L2 Label', default='Below Expectations')
    l2_incentive = fields.Float(string='L2 Incentive (%)', default=5)

    l3_min       = fields.Float(string='L3 Min (%)', default=70)
    l3_max       = fields.Float(string='L3 Max (%)', default=79)
    l3_label     = fields.Char(string='L3 Label', default='Meets Expectations')
    l3_incentive = fields.Float(string='L3 Incentive (%)', default=10)

    l4_min       = fields.Float(string='L4 Min (%)', default=80)
    l4_max       = fields.Float(string='L4 Max (%)', default=89)
    l4_label     = fields.Char(string='L4 Label', default='Exceeds Expectations')
    l4_incentive = fields.Float(string='L4 Incentive (%)', default=15)

    l5_min       = fields.Float(string='L5 Min (%)', default=90)
    l5_max       = fields.Float(string='L5 Max (%)', default=100)
    l5_label     = fields.Char(string='L5 Label', default='Outstanding')
    l5_incentive = fields.Float(string='L5 Incentive (%)', default=20)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            emp = self.employee_id
            self.staff_id      = emp.id_card_no or ''
            self.designation   = emp.job_id.name if emp.job_id else emp.job_title or ''
            self.department_id = emp.department_id if emp.department_id else False
        else:
            self.staff_id      = ''
            self.designation   = ''
            self.department_id = False

    def get_level_info(self, percent):
        """
        percent — 0.0~1.0 scale (widget='percentage' এর জন্য)
        score_min/max — 0~100 scale এ stored
        তাই compare করার আগে * 100 করছি
        """
        self.ensure_one()
        p = percent * 100
        levels = [
            ('l5', self.l5_label, self.l5_incentive, self.l5_min, self.l5_max),
            ('l4', self.l4_label, self.l4_incentive, self.l4_min, self.l4_max),
            ('l3', self.l3_label, self.l3_incentive, self.l3_min, self.l3_max),
            ('l2', self.l2_label, self.l2_incentive, self.l2_min, self.l2_max),
            ('l1', self.l1_label, self.l1_incentive, self.l1_min, self.l1_max),
        ]
        for level, label, incentive, min_val, max_val in levels:
            if min_val <= p <= max_val:
                return level, label, incentive
        if p > self.l5_max:
            return 'l5', self.l5_label, self.l5_incentive
        return 'l1', self.l1_label, self.l1_incentive

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('kpi.config') or 'New'
                )
            if vals.get('employee_id'):
                emp = self.env['hr.employee'].browse(vals['employee_id'])
                vals['staff_id']      = emp.id_card_no or ''
                vals['designation']   = emp.job_id.name if emp.job_id else emp.job_title or ''
                vals['department_id'] = emp.department_id.id if emp.department_id else False
        return super().create(vals_list)

    @api.constrains('employee_id', 'active')
    def _check_unique_active(self):
        for rec in self:
            if rec.active:
                duplicate = self.search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('active', '=', True),
                    ('id', '!=', rec.id),
                ])
                if duplicate:
                    raise UserError(
                        'Employee "%s" already has an active KPI Configuration. '
                        'Please deactivate the existing one first.'
                        % rec.employee_id.name
                    )

    def write(self, vals):
        if vals.get('employee_id'):
            emp = self.env['hr.employee'].browse(vals['employee_id'])
            vals['staff_id']      = emp.id_card_no or ''
            vals['designation']   = emp.job_id.name if emp.job_id else emp.job_title or ''
            vals['department_id'] = emp.department_id.id if emp.department_id else False
        return super().write(vals)


class KpiConfigTask(models.Model):
    _name = 'kpi.config.task'
    _description = 'KPI Configuration Task Line'
    _order = 'sequence'

    sequence      = fields.Integer(default=10)
    kpi_config_id = fields.Many2one(
        'kpi.config', string='KPI Config', ondelete='cascade'
    )
    task_name    = fields.Char(string='Task Name', required=True)
    description  = fields.Text(string='Description')
    target_value = fields.Float(string='Target Value', required=True)
    uom          = fields.Char(string='Unit', help='e.g. calls, reports, visits')