from odoo import fields, models


class HRJobGradeType(models.Model):
    """ Create HR Job grade type like(Managerial, Executive etc.) """
    _name = 'hr.job.grade.type'
    _description = 'HR Job Grade Type'

    name = fields.Char(string="Grade Type", required=True, trim=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Type name already exists !"),
    ]
