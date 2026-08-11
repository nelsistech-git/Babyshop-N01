from odoo import fields, models


class HrApplicantActivities(models.Model):
    _name = 'hr.applicant.activities'
    _description = 'Applicant Activities'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete="cascade")

    activity_name = fields.Char(string="Nature of Activity", help="Name & Nature of Activity")
    award = fields.Char(string="Honors / Awards / Prize (if any)")
