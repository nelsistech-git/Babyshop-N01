from odoo import api, exceptions, fields, models, _
from odoo.addons.helper import validator
from odoo.exceptions import UserError


class InheritedStockLocCustomStock(models.Model):
    _inherit = "stock.location"
    _description = "Inherited Stock Location for new Features"

    is_work_loc = fields.Boolean(string="Is a Work Location?", default=False)  # Set True by Context
    is_work_loc_default = fields.Boolean(string="Is Default Work Location?", default=False)
    is_loss_loc = fields.Boolean(string="Is a Loss Location?", default=False)  # Set True by Context
    is_qc_loc = fields.Boolean(string="Is a QC Location?", default=False)  # Set True by Context
    store_sl = fields.Integer(string="SL", default=0, help="SL can be maximum 5 digits")
    store_no = fields.Char(string="Location No", size=50, copy=False)
    store_zone_id = fields.Many2one("store.zone", string="Area/Territory", ondelete="cascade")
    store_address = fields.Text(string="Address", help="Address can be maximum 200 characters")
    district_id = fields.Many2one("district", string="District", ondelete="cascade")
    division_id = fields.Many2one("division", string="Division", ondelete="cascade")
    store_manager_id = fields.Many2one("res.users", string="Location Manager", ondelete="cascade")
    area_manager_id = fields.Many2one("res.users", string="Area Manager")
    store_shelf = fields.Integer(string="Shelf", help="Shelf can be maximum 5 digits")
    store_hanging = fields.Integer(string="Hanging", help="Hanging can be maximum 5 digits")
    display_area = fields.Integer(string="Display Area (SFT)", help="Display area can be maximum 5 digits")
    store_area = fields.Integer(string="Area (SFT)", help="Internal go down area can be maximum 5 digits")
    total_area = fields.Char(string="Total Area (SFT)", compute='_get_total_area', store=True)
    shop_capacity = fields.Integer(string="Capacity", help="In pairs capacity can be maximum 4 digits")
    cctv_link = fields.Char(help="Add URL for the CCTV link here")
    vat_reg = fields.Char(size=100, copy=False, help="Add VAT registration number here")
    bin_no = fields.Char(size=100, string='BIN No.', copy=False, help="Add BIN number here")
    tin_no = fields.Char(size=100, string='TIN No.', copy=False, help="Add TIN number here")
    mobile = fields.Char(string="Contact Mobile", size=20, copy=False, help="Enter contact Mobile here")
    phone = fields.Char(string="Contact Phone", size=20, copy=False, help="Enter contact Phone here")
    email = fields.Char(string="Contact Email", size=50, copy=False, help="Enter contact Email here")
    shop_type_id = fields.Many2one("shop.type", string="Location Category", ondelete="cascade")
    agreement_signup_date = fields.Date(string="Sign up Date", default=fields.Date.today())
    agreement_expire_date = fields.Date(string="Expire Date", default=fields.Date.today())
    shop_type_id_name = fields.Char(string='Type Name', related="shop_type_id.name")
    commission = fields.Integer(string="Commission (%)", help="Commission(%) can be maximum 5 digits")
    rent = fields.Integer(string="Rent Amount (Monthly)", help="Rent Amount(Monthly) can be maximum 7 digits")
    increment_rate = fields.Integer(string="Increment Rate (%)", help="Increment rate(%) can be maximum 5 digits")
    renew_month = fields.Integer(string="Renew After (Months)", help="Renew After(In months) can be maximum 4 digits")
    last_renew_date = fields.Date(string="Last Renew Date", default=fields.Date.today())
    before_notification_day = fields.Integer(string="Notify Before (Days)",
                                             help="Notify Before(In days) can be maximum 3 digits")
    attachement_file_ids = fields.Many2many('ir.attachment', 'stock_location_ir_attachments_rel', 'shop_id',
                                            'attachment_id', string='Attachments', help="Attach files here")
    joint_venture_flag = fields.Boolean(default=False)
    rented_flag = fields.Boolean(default=False)
    godown_ids = fields.Many2many("store.godown", string="External Go-down", column1='store_no', column2='godown_id')
    # land_owner_ids = fields.One2many("landowner.details", "store_id", string="Land Owner Details")
    shop_user_ids = fields.Many2many(comodel_name="res.users",
                                     relation='shop_users_stock_location_rel',
                                     string="Salesman Information", column1='stock_location_id',
                                     column2='res_user_id', ondelete='cascade')
    type = fields.Selection(
        [('ho', "Head Office"),  # Head office
         ('branch', "Branch/Site Office"),  # Branch/Site office
         ('project', "Project"),  # Project
         ('factory', "Factory"),  # Factory
         ('shop', "Shop"),  # Shop/Is Retail
         ('cdc', "CDC"),  # CDC Shop
         ('guarantee', "Guarantee"),  # Guarantee/Warranty Shop
         ('ecommerce', "E-commerce"),  # Ecommerce Shop
         ('corporate', "Corporate"),  # Corporate Shop
         ('whole_sale', "Whole Sale"),  # Whole Sale Shop
         ('defective_supp', "Defective Supplier"),   # Defective Supplier Shop
         ('service', "Service")   # Service center
         ])
    login_lock = fields.Boolean(string="Login Locked?", default=False)
    state = fields.Selection([('draft', "Draft"), ('confirm', "Confirmed"), ('done', "Done"), ('cancel', "Cancelled")],
                             default="draft")
    payment_journal_id = fields.Many2one('account.journal', string='Payment Journal Type')
    payment_account_id = fields.Many2one('account.account', string='Payment Account',)
    receive_journal_id = fields.Many2one('account.journal', string='Receive Journal Type')
    receive_account_id = fields.Many2one('account.account', string='Receive Account',)
    loan_account_id = fields.Many2one('account.account', string='Loan Account',)
    tailor_expense_account_id = fields.Many2one('account.account', string='Tailor Expense Account',)
    tailor_income_account_id = fields.Many2one('account.account', string='Tailor Income Account',)

    # manufacturing account
    mo_debit_account_id = fields.Many2one('account.account', string='Manufacturing Debit Account', help='Manufacturing Debit Account')
    mo_credit_account_id = fields.Many2one('account.account', string='Manufacturing Credit Account', help='Manufacturing Credit Account')
    mfg_wip_account_id = fields.Many2one('account.account', string='WIP Account', help='MFG WIP Account')

    # manufacturing other cost account
    other_cost_debit_account_id = fields.Many2one('account.account', string='Other Cost Debit Account',)
    other_cost_credit_account_id = fields.Many2one('account.account', string='Other Cost Credit Account',)

    inter_company_id = fields.Many2one("internal.company", string="Inter Company", ondelete="restrict")
    is_inter_company_journal = fields.Boolean(default=True, string="Inter Company Journal?")
    inter_comp_tr_acc_id = fields.Many2one('account.account', string='Inter Company Receivable (Asset) Account',)
    inter_comp_tr_pay_acc_id = fields.Many2one('account.account', string='Inter Company Payable (Liability) Account',)

    is_transfer_journal = fields.Boolean(default=True, string="Transfer Journal?")
    transfer_st_acc_id = fields.Many2one('account.account', string='Transfer Default Stock Account', help='Internal Transfer Default Strock Account')

    store_type_rpt = fields.Selection([('wh', "Central Store"), ('production', "Production Store"), ('other', "Others")],
                             default="other", string="Store Type (Report)")


    @api.onchange('inter_company_id')
    def _onchange_inter_company_id(self):
        if self.inter_company_id:
            self.inter_comp_tr_acc_id = self.inter_company_id.receivable_acc_id or None
            self.inter_comp_tr_pay_acc_id = self.inter_company_id.payable_acc_id or None

    # @api.onchange('payment_journal_id')
    # def _onchange_payment_journal_id(self):
    #     accounts = []
    #     journals = self.env['account.journal'].search([('id', '=', self.payment_journal_id.id)])
    #     for journal in journals:
    #         accounts.append(journal.default_credit_account_id.id)
    #     return {'domain': {'payment_account_id': [('id', 'in', accounts)]}}

    # @api.onchange('receive_journal_id')
    # def _onchange_receive_journal_id(self):
    #     accounts = []
    #     journals = self.env['account.journal'].search([('id', '=', self.receive_journal_id.id)])
    #     for journal in journals:
    #         accounts.append(journal.default_credit_account_id.id)
    #     return {'domain': {'receive_account_id': [('id', 'in', accounts)]}}

    # ------------ Compute method --------------
    @api.depends('display_area', 'store_area')
    def _get_total_area(self):
        for record in self:
            record.total_area = record.display_area + record.store_area

    # -----------on change methods ---------------

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.onchange("vat_reg")
    def _onchange_vat_reg(self):
        if self.vat_reg:
            self.vat_reg = str(self.vat_reg).strip()

    @api.onchange("phone")
    def _onchange_phone(self):
        if self.phone:
            self.phone = str(self.phone).strip()

    @api.onchange("mobile")
    def _onchange_mobile(self):
        if self.mobile:
            self.mobile = str(self.mobile).strip()

    @api.onchange("email")
    def _onchange_email(self):
        if self.email:
            self.email = str(self.email).strip()

    #     @api.onchange("store_classification_id")
    #     def _onchange_store_classification_id(self):
    #         if self.store_classification_id:
    #             self.class_grade_id = False

    @api.onchange('division_id')
    def _onchange_division(self):
        self.district_id = False

    @api.onchange("store_shelf", "store_hanging", "commission", "display_area", "store_area", "increment_rate")
    def _onchange_shelf_hanging_commission_area_rate_value(self):
        length = 5
        if len(str(self.store_shelf)) > length:
            field_name = "Shelf"
            store_shelf = self.store_shelf
            self.store_shelf = validator._check_integer(self, store_shelf, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.store_hanging)) > length:
            field_name = "Hanging"
            store_hanging = self.store_hanging
            self.store_hanging = validator._check_integer(self, store_hanging, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.commission)) > length:
            field_name = "Commission(%)"
            commission = self.commission
            self.commission = validator._check_integer(self, commission, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.display_area)) > length:
            field_name = "Display Area"
            display_area = self.display_area
            self.display_area = validator._check_integer(self, display_area, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.store_area)) > length:
            field_name = "Area"
            store_area = self.store_area
            self.store_area = validator._check_integer(self, store_area, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.increment_rate)) > length:
            field_name = "Increment Rate(%)"
            increment_rate = self.increment_rate
            self.increment_rate = validator._check_integer(self, increment_rate, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("shop_capacity", "renew_month")
    def _onchange_shop_capacity_renew_month_value(self):
        length = 4
        if len(str(self.shop_capacity)) > length:
            field_name = "Capacity(In pair)"
            shop_capacity = self.shop_capacity
            self.shop_capacity = validator._check_integer(self, shop_capacity, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

        if len(str(self.renew_month)) > length:
            field_name = "Renew after(In months)"
            renew_month = self.renew_month
            self.renew_month = validator._check_integer(self, renew_month, length)

            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("rent")
    def _onchange_rent_value(self):
        length = 7
        if len(str(self.rent)) > length:
            field_name = "Rent Amount(Monthly)"
            rent = self.rent
            self.rent = validator._check_integer(self, rent, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("before_notification_day")
    def _onchange_before_notification_day_value(self):
        length = 3
        if len(str(self.before_notification_day)) > length:
            field_name = "Notify Before(In days)"
            before_notification_day = self.before_notification_day
            self.before_notification_day = validator._check_integer(self, before_notification_day, length)
            return validator._get_number_length_warning_msg(self, field_name, length)

    @api.onchange("shop_type_id")
    def _onchange_shop_type_id(self):
        if self.shop_type_id:
            shop_type_name = str(self.shop_type_id.name).strip().upper()
            if shop_type_name == 'JOINT VENTURE':
                self.rented_flag = False
                self.joint_venture_flag = True
            elif shop_type_name == 'RENTED':
                self.joint_venture_flag = False
                self.rented_flag = True
            else:
                self.joint_venture_flag = False
                self.rented_flag = False

    # ----------constrains methods---------------
    @api.constrains('store_address')
    def _check_store_address_length(self):
        limit = 200
        record = self.store_address
        field_name = "Address"
        validator._check_length(self, record, limit, field_name)

    @api.constrains('name', 'store_no')
    def _check_unique_constraint(self):
        msg1 = "Location name"
        msg2 = "Location No."
        envObj = self.env['stock.location']
        conditionList1 = [('company_id', '=', self.company_id.id), ('name', '=ilike', self.name)]
        conditionList2 = [('company_id', '=', self.company_id.id), ('store_no', '=ilike', self.store_no)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg1)
        validator.check_duplicate_value(self, envObj, conditionList2, msg2)

    @api.constrains('increment_rate', 'rent', 'renew_month', 'before_notification_day')
    def _check_negative_conditional_fields_rented(self):
        if self.increment_rate < 0 or self.rent < 0 or self.renew_month < 0 or self.before_notification_day < 0:
            raise exceptions.ValidationError(_(
                'Rent amount(Monthly) / Increment rate(%) / Renew after(In months) / Notify Before(In days) should be positive number!'))

    @api.constrains('commission')
    def _check_negative_commission(self):
        if self.commission < 0:
            raise exceptions.ValidationError(_('Commission(%) should be positive number!'))

    @api.constrains('agreement_signup_date', 'agreement_expire_date')
    def _check_agreement_date(self):
        if self.agreement_expire_date < self.agreement_signup_date:
            raise exceptions.ValidationError(_('Agreement expire date can not be earlier than agreement sign up date!'))

    @api.constrains('store_shelf', 'store_hanging', 'display_area', 'store_area')
    def _check_negative(self):
        if self.store_shelf < 0 or self.store_hanging < 0 or self.display_area < 0 or self.store_area < 0:
            raise exceptions.ValidationError(_('Shelf / Hanging / Display Area / Area should be positive number!'))

    @api.constrains('shop_capacity')
    def _check_negative_shop_capacity(self):
        if self.shop_capacity < 0:
            raise exceptions.ValidationError(_('Capacity(In pair) should be positive number!'))

    def action_confirm(self):
        res = {}
        if not self.store_no:
            comp_code = self.company_id.short_code
            max_sl = 1
            sl_row = self.env['stock.location'].search(
                [('company_id', '=', self.company_id.id), '|', ('active', '=', True), ('active', '=', False)],
                order="store_sl desc", limit=1)
            if sl_row:
                max_sl = sl_row[0].store_sl + 1

            # new_seq = self.env['ir.sequence'].get('store')
            # if new_seq:
            res['store_sl'] = max_sl
            if comp_code == False:
                raise UserError(
                    _("Short code is not set in the company. Please go to settings and set a short code for the company.")
                )
            else:
                res['store_no'] = str(comp_code) + str(max_sl).zfill(3)
                self.write(res)
        self.state = "confirm"

    def action_done(self):
        self.state = "done"

    def action_cancel(self):
        self.state = "cancel"

    def action_draft(self):
        self.state = "draft"

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s (copy)') % self.name)

        return super(InheritedStockLocCustomStock, self).copy(default)

    def unlink(self):
        for store in self:
            if store.state != 'draft':
                raise UserError(_("Only 'Draft' record can be deleted!"))
        return super(InheritedStockLocCustomStock, self).unlink()

    # def name_get(self):
    #     res = []
    #     for location in self:
    #         if location.store_no:
    #             name = str(location.name) + ' (' + str(location.store_no) + ')'
    #         else:
    #             name = location.name or ""
    #         if self._context.get('show_address'):
    #             name = name + "\n" + str(location._display_address(without_company=True))
    #         name = name.replace('\n\n', '\n')
    #         name = name.replace('\n\n', '\n')
    #         res.append((location.id, name))
    #     return res

    def _display_address(self, without_company=False):
        return self.store_address or ""

#         # get the address format
#         address_format = self._get_address_format()
#         args = {
#             'state_code': self.state_id.code or '',
#             'state_name': self.state_id.name or '',
#             'country_code': self.country_id.code or '',
#             'country_name': self._get_country_name(),
#             'company_name': self.commercial_company_name or '',
#         }
#         for field in self._formatting_address_fields():
#             args[field] = getattr(self, field) or ''
#         if without_company:
#             args['company_name'] = ''
#         elif self.commercial_company_name:
#             address_format = '%(company_name)s\n' + address_format
#         return address_format % args