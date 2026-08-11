# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    sh_hm_hide_menu_ids = fields.Many2many(
        comodel_name="ir.ui.menu",
        relation="rel_sh_hm_hide_menu_ir_ui_menu",
        string="Hide Menu"
    )

    menu_template_ids = fields.Many2many('sh.hide.menu.template',string="Menu Templates",inverse = "inverse_hide_menu_template")

    def inverse_hide_menu_template(self):

        if self.menu_template_ids:

            for menu in self.sh_hm_hide_menu_ids.ids:
                self.write({
                    'sh_hm_hide_menu_ids' : [(3,menu)]
                })

            menus = self.menu_template_ids.mapped('menu_ids')

            for menu in menus:
                self.write ({
                    'sh_hm_hide_menu_ids' : [(4,menu.id)],
                })
class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.returns('self')
    def _filter_visible_menus(self):
        """ Filter `self` to only keep the menu items that should be visible in
            the menu hierarchy of the current user.
            Uses a cache for speeding up the computation.
        """
        # for clear caches must required in odoo v12
        # not necessary in odoov9 to odoov11
        #self.env['ir.ui.menu'].sudo().clear_caches()

        res = super(IrUiMenu, self)._filter_visible_menus()
        if(
            res and
            self.env.user and
            self.env.user.sh_hm_hide_menu_ids
        ):
            return res.filtered(lambda m: m.id not in self.env.user.sh_hm_hide_menu_ids.ids)
        return res
