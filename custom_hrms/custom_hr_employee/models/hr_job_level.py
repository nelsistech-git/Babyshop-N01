from odoo import fields, models


class HRJobLevel(models.Model):
    """ Fields list Job Level """

    _name = "hr.job.level"
    _description = "HR Job Level"

    name = fields.Char(string="Job Level", required=True, trim=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Level name already exists!"),
    ]
