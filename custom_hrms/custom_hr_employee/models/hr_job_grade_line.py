from odoo import fields, models, api
from odoo.addons.helper import validator


class HRJobGradeLine(models.Model):
    """ HR Job grade Line """
    _name = 'hr.job.grade.line'
    _description = 'HR Job Grade Line'

    job_grade = fields.Many2one('hr.job.grade', string="Job Grade")
    name = fields.Many2one("hr.job", string="Designation", required=True)  # job_id

    dept_name = fields.Many2one("hr.department", string="Department", related='name.department_id', store=True)

    grade_type = fields.Many2one("hr.job.grade.type", string="Grade Type", related='job_grade.grade_type')
    job_level = fields.Many2one("hr.job.level", string="Job Level", related='job_grade.job_level')

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        grade_name = ''
        exist_row = self.env['hr.job.grade.line'].search([('name', '=', self.name.id)], limit=1)
        if exist_row:
            grade_name = exist_row[0].job_grade.name

        msg = "Designation '%s' in Job Grade '%s'" % (self.name.name, grade_name)
        envObj = self.env['hr.job.grade.line']
        conditionList1 = [('name', '=', self.name.id)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)
