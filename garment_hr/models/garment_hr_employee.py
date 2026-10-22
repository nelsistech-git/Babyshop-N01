# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Master (SRS section 6) — garment.hr.employee. Worker Profile
Management (SRS section 8) is folded in directly as fields, mirroring the
Buyer 360 / Supplier Master pattern used throughout this suite, rather
than a separate 1-to-1 model.
"""
from datetime import date, timedelta
from odoo import api, fields, models, _


class GarmentHrDocument(models.Model):
    _name = 'garment.hr.document'
    _description = 'Garment HR Document'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', ondelete='cascade')
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('nid', 'National ID'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ], string='Document Type', required=True)

    file = fields.Binary(string='File', required=True)
    filename = fields.Char(string='File Name')
    expiry_date = fields.Date(string='Expiry Date')
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_is_expiring_soon',
        store=True
    )

    @api.depends('expiry_date')
    def _compute_is_expiring_soon(self):
        today = date.today()
        warning_period = today + timedelta(days=30)
        for record in self:
            if record.expiry_date:
                record.is_expiring_soon = today <= record.expiry_date <= warning_period
            else:
                record.is_expiring_soon = False


class GarmentHrEmployee(models.Model):
    _name = 'garment.hr.employee'
    _description = 'Garment Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    employee_id = fields.Char(string='Employee ID', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Full Name', required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Related User', ondelete='restrict',
                              help='Optional link for portal/ESS access.')
    photo = fields.Binary(string='Photo', attachment=True)

    # Basic Information
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other'),
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'), ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'), ('o+', 'O+'), ('o-', 'O-'),
    ], string='Blood Group')
    father_name = fields.Char(string="Father's Name")
    mother_name = fields.Char(string="Mother's Name")
    national_id = fields.Char(string='National ID')
    mobile = fields.Char(string='Mobile')
    present_address = fields.Char(string='Present Address')
    permanent_address = fields.Char(string='Permanent Address')
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_number = fields.Char(string='Emergency Contact Number')

    # Employment Details
    department_id = fields.Many2one('garment.hr.department', string='Department', required=True, tracking=True)
    designation_id = fields.Many2one('garment.hr.designation', string='Designation', required=True, tracking=True)
    employee_category = fields.Selection([
        ('worker', 'Worker'), ('supervisor', 'Supervisor'), ('staff', 'Staff'), ('officer', 'Officer'),
        ('management', 'Management'), ('executive', 'Executive'), ('contract', 'Contract Employee'),
    ], string='Employee Category', related='designation_id.employee_category', store=True)
    work_location = fields.Char(string='Work Location', help='Factory / unit / floor this employee is based at.')
    joining_date = fields.Date(string='Joining Date', tracking=True)
    employment_type = fields.Selection([
        ('permanent', 'Permanent'), ('probation', 'Probation'), ('contractual', 'Contractual'), ('casual', 'Casual'),
    ], string='Employment Type', default='probation')
    reporting_manager_id = fields.Many2one('garment.hr.employee', string='Reporting Manager')
    line_assignment = fields.Char(string='Production Line Assignment')
    shift_id = fields.Many2one('garment.hr.shift', string='Current Shift')

    # Worker Profile fields (folded in from SRS section 8)
    skill_level = fields.Selection([
        ('trainee', 'Trainee'), ('junior', 'Junior Operator'), ('senior', 'Senior Operator'), ('expert', 'Expert'),
    ], string='Skill Level')
    is_piece_rate_eligible = fields.Boolean(string='Piece-Rate Eligible',
                                            related='designation_id.is_piece_rate_eligible')
    machine_operated = fields.Char(string='Machine Operated')

    status = fields.Selection([
        ('active', 'Active'), ('on_leave', 'On Leave'), ('suspended', 'Suspended'),
        ('resigned', 'Resigned'), ('terminated', 'Terminated'),
    ], string='Status', default='active', tracking=True)

    document_ids = fields.One2many('garment.hr.document', 'employee_id', string='Documents')
    attendance_ids = fields.One2many('garment.hr.attendance', 'employee_id', string='Attendance')
    leave_ids = fields.One2many('garment.hr.leave', 'employee_id', string='Leaves')
    payroll_ids = fields.One2many('garment.hr.payroll', 'employee_id', string='Payroll')
    training_ids = fields.One2many('garment.hr.training', 'employee_id', string='Trainings')
    skill_matrix_ids = fields.One2many('garment.hr.skill.matrix', 'employee_id', string='Skill Matrix')
    performance_ids = fields.One2many('garment.hr.performance', 'employee_id', string='Performance Reviews')
    discipline_ids = fields.One2many('garment.hr.discipline', 'employee_id', string='Disciplinary Records')
    shift_assignment_ids = fields.One2many('garment.hr.shift.assignment', 'employee_id', string='Shift Assignments')
    bonus_ids = fields.One2many('garment.hr.bonus', 'employee_id', string='Bonuses')
    incentive_ids = fields.One2many('garment.hr.incentive', 'employee_id', string='Production Incentives')
    loan_ids = fields.One2many('garment.hr.loan', 'employee_id', string='Loans / Advances')
    complaint_ids = fields.One2many('garment.hr.complaint', 'employee_id', string='Complaints')
    exit_ids = fields.One2many('garment.hr.exit', 'employee_id', string='Exit Records')

    ai_retention_risk_note = fields.Text(string='AI Retention Risk', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('employee_id_uniq', 'unique(employee_id, company_id)', 'Employee ID must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id', _('New')) == _('New'):
                vals['employee_id'] = self.env['ir.sequence'].next_by_code('garment.hr.employee') or _('New')
        return super().create(vals_list)

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.predict_employee_retention_risk(rec)
            rec.write({'ai_retention_risk_note': note, 'ai_last_run': fields.Datetime.now()})
        return True