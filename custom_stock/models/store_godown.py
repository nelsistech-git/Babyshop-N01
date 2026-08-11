from odoo import api, exceptions, fields, models, _
from odoo.addons.helper import validator


class StoreGodown(models.Model):
    _name = "store.godown"
    _description = "Store Go-down"

    name = fields.Char(string="Name", size=100, required=True, help="Name can be maximum 100 characters")
    godown_address = fields.Text(string="Address", help="Address can be maximum 200 characters")
    godown_shelf = fields.Integer(string="Shelf", help="Shelf can be maximum 5 digits")
    godown_area = fields.Integer(string="Area (SFT)", help="Go-down area can be maximum 5 digits")

    godown_agreement_signup_date = fields.Date(string="Sign up Date", default=fields.Date.today())
    godown_agreement_expire_date = fields.Date(string="Expire Date", default=fields.Date.today())
    rent = fields.Integer(string="Rent Amount (Monthly)", help="Rent Amount(Monthly) can be maximum 7 digits")
    increment_rate = fields.Integer(string="Increment Rate (%)", help="Increment Rate can be maximum 5 digits")
    # comment-for-upgrade
    # godown_owner_ids = fields.One2many("godownowner.details", "godown_id", string="Go-down owner details")

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.onchange("godown_shelf")
    def _onchange_godown_shelf_value(self):
        length = 5
        if len(str(self.godown_shelf)) > length:
            field_name = "Shelf"
            godown_shelf = self.godown_shelf
            self.godown_shelf = validator._check_integer(self, godown_shelf, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("godown_area")
    def _onchange_godown_area(self):
        length = 5
        if len(str(self.godown_area)) > length:
            field_name = "Go-down area"
            godown_area = self.godown_area
            self.godown_area = validator._check_integer(self, godown_area, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("rent")
    def _onchange_rent_value(self):
        length = 7
        if len(str(self.rent)) > length:
            field_name = "Rent Amount(Monthly)"
            rent = self.rent
            self.rent = validator._check_integer(self, rent, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("increment_rate")
    def _onchange_increment_rate_value(self):
        length = 5
        if len(str(self.increment_rate)) > length:
            field_name = "Increment Rate(%)"
            increment_rate = self.increment_rate
            self.increment_rate = validator._check_integer(self, increment_rate, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.constrains('godown_agreement_signup_date', 'godown_agreement_expire_date')
    def _check_agreement_date(self):
        if self.godown_agreement_expire_date < self.godown_agreement_signup_date:
            raise exceptions.ValidationError(_('Agreement expire date can not be earlier than agreement sign up date!'))

    @api.constrains('godown_shelf', 'godown_area')
    def _check_negative(self):
        if self.godown_shelf < 0 or self.godown_area < 0:
            raise exceptions.ValidationError(_('Shelf / Go-down area should be positive number!'))

    @api.constrains('godown_address')
    def _check_godown_address_length(self):
        limit = 200
        record = self.godown_address
        field_name = "Address"
        validator._check_length(self, record, limit, field_name)

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Go-down name"
        envObj = self.env['store.godown']
        conditionList = [('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)

    @api.constrains('increment_rate', 'rent')
    def _check_negative_conditional_fields_rented(self):
        if self.increment_rate < 0 or self.rent < 0:
            raise exceptions.ValidationError(_('Rent amount(Monthly) / Increment rate(%) should be positive number!'))
