from odoo import fields, models
from odoo.exceptions import ValidationError


class TechnicianChangePasswordWizard(models.TransientModel):
    _name = "technician.change.password.wizard"
    _description = "Change Password Wizard"

    user_id = fields.Many2one(
        'res.users',
        string="User Name",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )

    password = fields.Char(
        string='Password',
        required=True,
    )

    def technician_change_password(self):
        self.ensure_one()

        if not self.password:
            raise ValidationError("Password cannot be empty.")

        self.user_id.sudo().write({
            'password': self.password
        })

        return {'type': 'ir.actions.act_window_close'}
        