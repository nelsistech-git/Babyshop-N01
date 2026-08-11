# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
# from openerp.exceptions import Warning
# from odoo.exceptions import Warning #odoo13
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order','mail.thread']

  #  @api.multi #odoo13
    def action_pos_order_send(self):
        if not self.partner_id:
            raise UserError(_('Customer not found on this Point of Sale Orders.'))
        self.ensure_one()
        template = self.env.ref('pos_order_report.email_template_edi_pos_orders', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='pos.order',
            default_res_ids=self.ids,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
#        