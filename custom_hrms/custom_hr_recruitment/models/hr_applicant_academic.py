from odoo import fields, models


class HrApplicantAcademic(models.Model):
    _name = 'hr.applicant.academic'
    _description = 'Applicant Academic'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete="cascade")

    exam_name = fields.Char('Exam Name')
    expire = fields.Boolean('Expire', help="Expire", default=False)
    start_date = fields.Date('Study years (FROM)')
    end_date = fields.Date('Study years (TO)')
    passing_year = fields.Char(string="Passing year")
    exam_held_year = fields.Char('Exam Held (Year)')
    institute_id = fields.Char(string='Name of School / College / University',
                               help="School, University, Company, Certification Authority")
    result = fields.Char(string="Result")
    study_field = fields.Char('Subject / Group', translate=True)
    board_id = fields.Char(string='University / Board with Country', help="University / Board with Country")
    scholarship_info = fields.Char(string="Scholarship / Distinction")
