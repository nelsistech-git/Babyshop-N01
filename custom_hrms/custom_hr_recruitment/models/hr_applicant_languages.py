from odoo import fields, models


class HrApplicantLanguages(models.Model):
	_name = 'hr.applicant.languages'
	_description = 'Applicant Languages'

	applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True)

	language = fields.Char(string="Language")
	reading_skill = fields.Selection(
		string='Reading',
		selection=[('good', 'Good'),
			('average', 'Average'), ('poor', 'Poor')],
		required=False)
	writing_skill = fields.Selection(
		string='Writing',
		selection=[('good', 'Good'),
			('average', 'Average'), ('poor', 'Poor')],
		required=False)
	speaking_skill = fields.Selection(
		string='Speaking',
		selection=[('good', 'Good'),
			('average', 'Average'), ('poor', 'Poor')],
		required=False)