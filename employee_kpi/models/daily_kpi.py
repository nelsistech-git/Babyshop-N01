import calendar
from odoo import models, fields, api
from odoo.exceptions import UserError


# ══════════════════════════════════════════════════════════════
# Daily KPI
# ══════════════════════════════════════════════════════════════

class DailyKpi(models.Model):
    _name = 'daily.kpi'
    _description = 'Daily KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # ── Reference & Status ────────────────────────────────────
    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # ── Employee Info ─────────────────────────────────────────
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True
    )
    designation = fields.Char(string='Designation', readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True
    )
    staff_id = fields.Char(string='Staff ID', readonly=True)
    date = fields.Date(
        string='Date', required=True,
        default=fields.Date.today, tracking=True
    )

    # ── KPI Lines ─────────────────────────────────────────────
    line_ids = fields.One2many(
        'daily.kpi.line', 'daily_kpi_id', string='KPI Tasks'
    )

    # ── Manager Remarks ───────────────────────────────────────
    manager_remarks = fields.Text(string='Manager Remarks')

    # ── Computed Totals ───────────────────────────────────────
    total_target = fields.Float(
        string='Total Target',
        compute='_compute_totals', store=True
    )
    total_achieved = fields.Float(
        string='Total Achieved',
        compute='_compute_totals', store=True
    )
    total_time_spent = fields.Float(
        string='Total Time Spent (hrs)',
        compute='_compute_totals', store=True
    )
    total_incentive = fields.Float(
        string='Total Incentive Amount',
        compute='_compute_totals', store=True
    )
    # 0.0~1.0 scale — widget="percentage" → 100% দেখাবে
    achievement_percent = fields.Float(
        string='Achievement %',
        compute='_compute_totals', store=True
    )
    kpi_level = fields.Selection([
        ('l1', 'L1'), ('l2', 'L2'), ('l3', 'L3'),
        ('l4', 'L4'), ('l5', 'L5'),
    ], string='KPI Level', compute='_compute_totals', store=True)
    incentive_percent = fields.Float(
        string='Incentive %',
        compute='_compute_totals', store=True
    )
    overall_rating = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], string='Overall Rating', compute='_compute_totals', store=True)

    # ── Onchange: auto-fill employee + load tasks ─────────────
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            emp = self.employee_id
            self.designation   = emp.job_id.name if emp.job_id else emp.job_title or ''
            self.department_id = emp.department_id if emp.department_id else False
            self.staff_id      = emp.id_card_no or ''

            config = self.env['kpi.config'].search([
                ('employee_id', '=', emp.id),
                ('active', '=', True),
            ], limit=1)
            if config and config.task_line_ids:
                self.line_ids = [(5, 0, 0)]
                self.line_ids = [
                    (0, 0, {
                        'task_name':    task.task_name,
                        'description':  task.description or '',
                        'target_value': task.target_value,
                    })
                    for task in config.task_line_ids
                ]
        else:
            self.designation   = ''
            self.department_id = False
            self.staff_id      = ''
            self.line_ids      = [(5, 0, 0)]

    # ── Helper: get kpi.config for employee ───────────────────
    def _get_kpi_config(self):
        self.ensure_one()
        config = self.env['kpi.config'].search([
            ('employee_id', '=', self.employee_id.id),
            ('active', '=', True),
        ], limit=1)
        if not config:
            config = self.env['kpi.config'].search([
                ('active', '=', True),
            ], limit=1)
        return config

    # ── Compute totals + level + incentive ────────────────────
    @api.depends(
        'line_ids.target_value',
        'line_ids.achieved_value',
        'line_ids.time_spent',
        'line_ids.incentive_amount',
        'employee_id',
    )
    def _compute_totals(self):
        for rec in self:
            lines           = rec.line_ids
            total_target    = sum(lines.mapped('target_value'))
            total_achieved  = sum(lines.mapped('achieved_value'))
            total_time      = sum(lines.mapped('time_spent'))
            total_incentive = sum(lines.mapped('incentive_amount'))

            rec.total_target     = total_target
            rec.total_achieved   = total_achieved
            rec.total_time_spent = total_time
            rec.total_incentive  = total_incentive

            # 0.0~1.0 scale (widget="percentage" → 100% দেখাবে)
            percent = (total_achieved / total_target) if total_target > 0 else 0.0
            rec.achievement_percent = percent

            # Level & incentive from kpi.config
            config = rec._get_kpi_config()
            if config:
                level, _label, incentive_pct = config.get_level_info(percent)
                rec.kpi_level         = level
                rec.incentive_percent = incentive_pct
            else:
                rec.kpi_level         = False
                rec.incentive_percent = 0.0

            # Overall rating (percent এখন 0.0~1.0)
            if percent >= 0.90:
                rec.overall_rating = 'outstanding'
            elif percent >= 0.80:
                rec.overall_rating = 'exceeds'
            elif percent >= 0.70:
                rec.overall_rating = 'meets'
            elif percent >= 0.60:
                rec.overall_rating = 'below'
            else:
                rec.overall_rating = 'unsatisfactory'

    # ── Sequence on create ────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('daily.kpi') or 'New'
                )
            if vals.get('employee_id'):
                emp = self.env['hr.employee'].browse(vals['employee_id'])
                vals['staff_id'] = emp.id_card_no or ''
                vals['designation'] = emp.job_id.name if emp.job_id else emp.job_title or ''
                vals['department_id'] = emp.department_id.id if emp.department_id else False
        return super().create(vals_list)

    # ── Workflow ──────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only Draft entries can be submitted.')
            if not rec.line_ids:
                raise UserError('Please add at least one KPI task.')
            rec.state = 'submitted'
            rec.message_post(body='Daily KPI submitted for review.')

    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('Only Submitted entries can be approved.')
            rec.state = 'approved'
            rec.message_post(body='Daily KPI approved.')

    def action_reject(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('Only Submitted entries can be rejected.')
            rec.state = 'rejected'
            rec.message_post(body='Daily KPI rejected.')

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'rejected':
                raise UserError('Only Rejected entries can be reset.')
            rec.state = 'draft'
            rec.message_post(body='Daily KPI reset to Draft.')

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'employee_kpi.action_report_daily_kpi'
        ).report_action(self)


# ══════════════════════════════════════════════════════════════
# Daily KPI Line
# ══════════════════════════════════════════════════════════════

class DailyKpiLine(models.Model):
    _name = 'daily.kpi.line'
    _description = 'Daily KPI Line'

    daily_kpi_id = fields.Many2one(
        'daily.kpi', string='Daily KPI', ondelete='cascade'
    )
    task_name      = fields.Char(string='Task Name', required=True)
    description    = fields.Text(string='Description')
    target_value   = fields.Float(string='Target')
    achieved_value = fields.Float(string='Achieved')
    # 0.0~1.0 scale
    achievement_percent = fields.Float(
        string='Achievement %',
        compute='_compute_achievement', store=True
    )
    time_spent = fields.Float(string='Time Spent (hrs)')
    kpi_level  = fields.Selection([
        ('l1', 'L1'), ('l2', 'L2'), ('l3', 'L3'),
        ('l4', 'L4'), ('l5', 'L5'),
    ], string='Level', compute='_compute_achievement', store=True)
    incentive_percent = fields.Float(
        string='Incentive %',
        compute='_compute_achievement', store=True
    )
    incentive_amount = fields.Float(
        string='Incentive Amount',
        compute='_compute_achievement', store=True
    )
    performance_rating = fields.Selection([
        ('outstanding',    'Outstanding'),
        ('exceeds',        'Exceeds'),
        ('meets',          'Meets'),
        ('below',          'Below'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], string='Rating', compute='_compute_achievement', store=True)
    remarks = fields.Text(string='Remarks')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # active_id দিয়ে চেষ্টা করো
        daily_kpi_id = (
                self.env.context.get('default_daily_kpi_id')
                or self.env.context.get('daily_kpi_id')
                or self.env.context.get('active_id')
        )
        if not daily_kpi_id:
            return defaults
        daily_kpi = self.env['daily.kpi'].browse(daily_kpi_id)
        if not daily_kpi or not daily_kpi.employee_id:
            return defaults
        config = self.env['kpi.config'].search([
            ('employee_id', '=', daily_kpi.employee_id.id),
            ('active', '=', True),
        ], limit=1)
        if not config:
            config = self.env['kpi.config'].search([('active', '=', True)], limit=1)
        if not config or not config.task_line_ids:
            return defaults
        existing_count = len(daily_kpi.line_ids)
        task_list = config.task_line_ids.sorted('sequence')
        if existing_count < len(task_list):
            next_task = task_list[existing_count]
            defaults['task_name'] = next_task.task_name
            defaults['description'] = next_task.description or ''
            defaults['target_value'] = next_task.target_value
        return defaults

    @api.depends('target_value', 'achieved_value', 'daily_kpi_id.employee_id')
    def _compute_achievement(self):
        for rec in self:
            # 0.0~1.0 scale
            percent = (
                rec.achieved_value / rec.target_value
                if rec.target_value > 0 else 0.0
            )
            rec.achievement_percent = percent

            employee = rec.daily_kpi_id.employee_id
            config = False
            if employee:
                config = self.env['kpi.config'].search([
                    ('employee_id', '=', employee.id),
                    ('active', '=', True),
                ], limit=1)
            if not config:
                config = self.env['kpi.config'].search(
                    [('active', '=', True)], limit=1
                )

            if config:
                level, _label, incentive_pct = config.get_level_info(percent)
                rec.kpi_level         = level
                rec.incentive_percent = incentive_pct
                rec.incentive_amount  = rec.achieved_value * incentive_pct / 100
            else:
                rec.kpi_level         = False
                rec.incentive_percent = 0.0
                rec.incentive_amount  = 0.0

            # percent এখন 0.0~1.0
            if percent >= 0.90:
                rec.performance_rating = 'outstanding'
            elif percent >= 0.80:
                rec.performance_rating = 'exceeds'
            elif percent >= 0.70:
                rec.performance_rating = 'meets'
            elif percent >= 0.60:
                rec.performance_rating = 'below'
            else:
                rec.performance_rating = 'unsatisfactory'


# ══════════════════════════════════════════════════════════════
# Monthly KPI Summary
# ══════════════════════════════════════════════════════════════

class MonthlyKpiSummary(models.Model):
    _name = 'monthly.kpi.summary'
    _description = 'Monthly KPI Summary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True
    )
    designation = fields.Char(string='Designation', readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True
    )
    staff_id = fields.Char(string='Staff ID', readonly=True)

    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    year = fields.Integer(
        string='Year', required=True,
        default=lambda self: fields.Date.today().year
    )

    total_working_days  = fields.Integer(string='Total Working Days', readonly=True)
    total_tasks         = fields.Integer(string='Total Tasks', readonly=True)
    total_target        = fields.Float(string='Total Target', readonly=True)
    total_achieved      = fields.Float(string='Total Achieved', readonly=True)
    total_time_spent    = fields.Float(string='Total Time Spent (hrs)', readonly=True)
    total_incentive     = fields.Float(string='Total Incentive Amount', readonly=True)
    # 0.0~1.0 scale
    achievement_percent = fields.Float(string='Achievement %', readonly=True)
    kpi_level = fields.Selection([
        ('l1', 'L1'), ('l2', 'L2'), ('l3', 'L3'),
        ('l4', 'L4'), ('l5', 'L5'),
    ], string='KPI Level', readonly=True)
    incentive_percent = fields.Float(string='Incentive %', readonly=True)
    daily_kpi_count   = fields.Integer(string='Daily Entries', readonly=True)

    manager_achievement_percent = fields.Float(
        string='Final Achievement % (Manager)', tracking=True
    )
    overall_rating = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], string='Overall Rating', tracking=True)
    manager_remarks = fields.Text(string='Manager Remarks')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            emp = self.employee_id
            self.designation   = emp.job_id.name if emp.job_id else emp.job_title or ''
            self.department_id = emp.department_id if emp.department_id else False
            self.staff_id      = emp.id_card_no or ''

    def _get_month_date_range(self):
        self.ensure_one()
        month_int = int(self.month)
        last_day  = calendar.monthrange(self.year, month_int)[1]
        date_from = '%s-%02d-01' % (self.year, month_int)
        date_to   = '%s-%02d-%s' % (self.year, month_int, last_day)
        return date_from, date_to

    def _get_approved_daily_kpis(self):
        self.ensure_one()
        date_from, date_to = self._get_month_date_range()
        return self.env['daily.kpi'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state',  '=', 'approved'),
            ('date',  '>=', date_from),
            ('date',  '<=', date_to),
        ])

    def _get_kpi_config(self):
        self.ensure_one()
        config = self.env['kpi.config'].search([
            ('employee_id', '=', self.employee_id.id),
            ('active', '=', True),
        ], limit=1)
        if not config:
            config = self.env['kpi.config'].search([('active', '=', True)], limit=1)
        return config

    def action_compute(self):
        for rec in self:
            if not rec.employee_id or not rec.month or not rec.year:
                raise UserError('Please select Employee, Month and Year first.')

            daily_kpis     = rec._get_approved_daily_kpis()
            total_target   = sum(daily_kpis.mapped('total_target'))
            total_achieved = sum(daily_kpis.mapped('total_achieved'))

            # 0.0~1.0 scale
            percent = (total_achieved / total_target) if total_target > 0 else 0.0

            kpi_cfg = rec._get_kpi_config()
            kpi_level, incentive_percent = False, 0.0
            if kpi_cfg:
                kpi_level, _label, incentive_percent = kpi_cfg.get_level_info(percent)

            if percent >= 0.90:   rating = 'outstanding'
            elif percent >= 0.80: rating = 'exceeds'
            elif percent >= 0.70: rating = 'meets'
            elif percent >= 0.60: rating = 'below'
            else:                 rating = 'unsatisfactory'

            rec.write({
                'total_working_days': len(daily_kpis),
                'total_tasks':        sum(len(d.line_ids) for d in daily_kpis),
                'total_target':       total_target,
                'total_achieved':     total_achieved,
                'total_time_spent':   sum(daily_kpis.mapped('total_time_spent')),
                'total_incentive':    sum(daily_kpis.mapped('total_incentive')),
                'achievement_percent': percent,
                'kpi_level':          kpi_level,
                'incentive_percent':  incentive_percent,
                'daily_kpi_count':    len(daily_kpis),
                'overall_rating':     rating,
                'manager_achievement_percent': percent,
            })
            rec.message_post(
                body='Monthly summary computed from %d daily KPI entries.' % len(daily_kpis)
            )
        return True

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only Draft summaries can be approved.')
            rec.state = 'approved'
            rec.message_post(body='Monthly KPI Summary approved.')

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body='Monthly KPI Summary reset to Draft.')

    def action_view_daily_kpis(self):
        self.ensure_one()
        daily_kpis = self._get_approved_daily_kpis()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Daily KPIs — %s' % self.employee_id.name,
            'res_model': 'daily.kpi',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', daily_kpis.ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('monthly.kpi.summary') or 'New'
                )
            if vals.get('employee_id'):
                emp = self.env['hr.employee'].browse(vals['employee_id'])
                vals['staff_id'] = emp.id_card_no or ''
                vals['designation'] = emp.job_id.name if emp.job_id else emp.job_title or ''
                vals['department_id'] = emp.department_id.id if emp.department_id else False
        return super().create(vals_list)


# ══════════════════════════════════════════════════════════════
# Yearly KPI Summary
# ══════════════════════════════════════════════════════════════

class YearlyKpiSummary(models.Model):
    _name = 'yearly.kpi.summary'
    _description = 'Yearly KPI Summary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, tracking=True
    )
    designation = fields.Char(string='Designation', readonly=True)
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True
    )
    staff_id = fields.Char(string='Staff ID', readonly=True)
    year = fields.Integer(
        string='Year', required=True,
        default=lambda self: fields.Date.today().year
    )

    total_working_days  = fields.Integer(string='Total Working Days', readonly=True)
    total_tasks         = fields.Integer(string='Total Tasks', readonly=True)
    total_target        = fields.Float(string='Total Target', readonly=True)
    total_achieved      = fields.Float(string='Total Achieved', readonly=True)
    total_time_spent    = fields.Float(string='Total Time Spent (hrs)', readonly=True)
    total_incentive     = fields.Float(string='Total Incentive Amount', readonly=True)
    # 0.0~1.0 scale
    achievement_percent = fields.Float(string='Achievement %', readonly=True)
    kpi_level = fields.Selection([
        ('l1', 'L1'), ('l2', 'L2'), ('l3', 'L3'),
        ('l4', 'L4'), ('l5', 'L5'),
    ], string='KPI Level', readonly=True)
    incentive_percent = fields.Float(string='Incentive %', readonly=True)
    monthly_count     = fields.Integer(string='Approved Monthly Summaries', readonly=True)

    monthly_line_ids = fields.One2many(
        'yearly.kpi.monthly.line', 'yearly_kpi_id',
        string='Monthly Breakdown'
    )

    manager_achievement_percent = fields.Float(
        string='Final Achievement % (Manager)', tracking=True
    )
    overall_rating = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], string='Overall Rating', tracking=True)
    manager_remarks = fields.Text(string='Manager Remarks')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            emp = self.employee_id
            self.designation   = emp.job_id.name if emp.job_id else emp.job_title or ''
            self.department_id = emp.department_id if emp.department_id else False
            self.staff_id      = emp.id_card_no or ''

    def _get_approved_monthly(self):
        self.ensure_one()
        return self.env['monthly.kpi.summary'].search([
            ('employee_id', '=', self.employee_id.id),
            ('year',  '=', self.year),
            ('state', '=', 'approved'),
        ], order='month')

    def _get_kpi_config(self):
        self.ensure_one()
        config = self.env['kpi.config'].search([
            ('employee_id', '=', self.employee_id.id),
            ('active', '=', True),
        ], limit=1)
        if not config:
            config = self.env['kpi.config'].search([('active', '=', True)], limit=1)
        return config

    def action_compute(self):
        month_names = {
            '1': 'January',  '2': 'February', '3': 'March',
            '4': 'April',    '5': 'May',       '6': 'June',
            '7': 'July',     '8': 'August',    '9': 'September',
            '10': 'October', '11': 'November', '12': 'December',
        }
        rating_labels = {
            'outstanding':    'Outstanding',
            'exceeds':        'Exceeds Expectations',
            'meets':          'Meets Expectations',
            'below':          'Below Expectations',
            'unsatisfactory': 'Unsatisfactory',
        }

        for rec in self:
            if not rec.employee_id or not rec.year:
                raise UserError('Please select Employee and Year first.')

            monthly        = rec._get_approved_monthly()
            total_target   = sum(monthly.mapped('total_target'))
            total_achieved = sum(monthly.mapped('total_achieved'))

            # 0.0~1.0 scale
            percent = (total_achieved / total_target) if total_target > 0 else 0.0

            kpi_cfg = rec._get_kpi_config()
            kpi_level, incentive_percent = False, 0.0
            if kpi_cfg:
                kpi_level, _label, incentive_percent = kpi_cfg.get_level_info(percent)

            if percent >= 0.90:   rating = 'outstanding'
            elif percent >= 0.80: rating = 'exceeds'
            elif percent >= 0.70: rating = 'meets'
            elif percent >= 0.60: rating = 'below'
            else:                 rating = 'unsatisfactory'

            rec.monthly_line_ids.unlink()
            lines = []
            for m in monthly:
                lines.append({
                    'yearly_kpi_id':      rec.id,
                    'month_name':         month_names.get(m.month, m.month),
                    'total_working_days': m.total_working_days,
                    'total_tasks':        m.total_tasks,
                    'total_target':       m.total_target,
                    'total_achieved':     m.total_achieved,
                    'total_incentive':    m.total_incentive,
                    'achievement_percent': m.manager_achievement_percent or m.achievement_percent,
                    'kpi_level':          m.kpi_level or '',
                    'overall_rating':     rating_labels.get(m.overall_rating, ''),
                })
            if lines:
                rec.env['yearly.kpi.monthly.line'].create(lines)

            rec.write({
                'total_working_days': sum(monthly.mapped('total_working_days')),
                'total_tasks':        sum(monthly.mapped('total_tasks')),
                'total_target':       total_target,
                'total_achieved':     total_achieved,
                'total_time_spent':   sum(monthly.mapped('total_time_spent')),
                'total_incentive':    sum(monthly.mapped('total_incentive')),
                'achievement_percent': percent,
                'kpi_level':          kpi_level,
                'incentive_percent':  incentive_percent,
                'monthly_count':      len(monthly),
                'overall_rating':     rating,
                'manager_achievement_percent': percent,
            })
            rec.message_post(
                body='Yearly summary computed from %d approved monthly summaries.' % len(monthly)
            )
        return True

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only Draft summaries can be approved.')
            rec.state = 'approved'
            rec.message_post(body='Yearly KPI Summary approved.')

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body='Yearly KPI Summary reset to Draft.')

    def action_view_monthly(self):
        self.ensure_one()
        monthly = self._get_approved_monthly()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Monthly Summaries — %s' % self.employee_id.name,
            'res_model': 'monthly.kpi.summary',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', monthly.ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('yearly.kpi.summary') or 'New'
                )
            if vals.get('employee_id'):
                emp = self.env['hr.employee'].browse(vals['employee_id'])
                vals['staff_id'] = emp.id_card_no or ''
                vals['designation'] = emp.job_id.name if emp.job_id else emp.job_title or ''
                vals['department_id'] = emp.department_id.id if emp.department_id else False
        return super().create(vals_list)


# ══════════════════════════════════════════════════════════════
# Yearly KPI Monthly Breakdown Line
# ══════════════════════════════════════════════════════════════

class YearlyKpiMonthlyLine(models.Model):
    _name = 'yearly.kpi.monthly.line'
    _description = 'Yearly KPI Monthly Breakdown'

    yearly_kpi_id       = fields.Many2one('yearly.kpi.summary', ondelete='cascade')
    month_name          = fields.Char(string='Month')
    total_working_days  = fields.Integer(string='Working Days')
    total_tasks         = fields.Integer(string='Tasks')
    total_target        = fields.Float(string='Target')
    total_achieved      = fields.Float(string='Achieved')
    total_incentive     = fields.Float(string='Incentive Amount')
    achievement_percent = fields.Float(string='Achievement %')
    kpi_level           = fields.Char(string='Level')
    overall_rating      = fields.Char(string='Rating')