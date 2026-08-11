
from odoo import api, fields, models

class HideMenuTemplateWizard(models.TransientModel):
    _name = 'sh.hide.menu.template.wizard'
    _description = "Wizard Hide Menu Template"

    name = fields.Char(string = "Name",required= True)
    menu_ids = fields.Many2many('ir.ui.menu')

    @api.model
    def default_get(self, fields):
        rec = super(HideMenuTemplateWizard, self).default_get(fields)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')
        res_users = self.env[active_model].browse(active_id)
        if res_users.sh_hm_hide_menu_ids.ids:
            rec['menu_ids'] = res_users.sh_hm_hide_menu_ids.ids
        return rec


    def create_hide_menu_template(self):

        self.env['sh.hide.menu.template'].create({
            'name':self.name,
            'menu_ids':self.menu_ids.ids,

        })
