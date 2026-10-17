# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, models
from odoo.exceptions import AccessError

GROUP_USER = 'nelsis_bond_inventory.group_bond_inventory_user'
GROUP_INSPECTOR = 'nelsis_bond_inventory.group_bond_inventory_inspector'
GROUP_APPROVER = 'nelsis_bond_inventory.group_bond_inventory_approver'
GROUP_MANAGER = 'nelsis_bond_inventory.group_bond_inventory_manager'


class BondReferenceMixin(models.AbstractModel):
    """Selection helpers for loosely coupled references to other Nelsis addons.

    The existing LC Management addon must never be assumed by name. The
    technical model name of the LC record is configured per company
    (res.company.bond_lc_model_name) after it has been discovered from the
    addon source. The customs document model of the shared contract
    (bond.warehouse.document) is offered only when that addon is installed.
    """
    _name = 'bond.inventory.reference.mixin'
    _description = 'Bond Inventory Reference Mixin'

    @api.model
    def _selection_lc_models(self):
        model_name = self.env.company.bond_lc_model_name
        if model_name and model_name in self.env:
            return [(model_name, self.env[model_name]._description or model_name)]
        return []

    @api.model
    def _selection_customs_models(self):
        model_name = 'bond.warehouse.document'
        if model_name in self.env:
            return [(model_name, self.env[model_name]._description or model_name)]
        return []

    def _bond_check_group(self, xml_id):
        """Raise unless the current user (or the superuser) is in the group."""
        if self.env.su:
            return
        if not self.env.user.has_group(xml_id):
            raise AccessError(_('You are not allowed to perform this operation (missing access group).'))

    def _bond_is_manager(self):
        return self.env.su or self.env.user.has_group(GROUP_MANAGER)
