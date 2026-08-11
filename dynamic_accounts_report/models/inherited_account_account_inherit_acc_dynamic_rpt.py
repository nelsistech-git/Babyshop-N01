from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError, UserError


class AccountAccountInheritDynamicRpt(models.Model):
    # _inherit = "account.account"
    _inherit = ['account.account', 'mail.thread']
    _description = "Account Account Inherit Dynamic Rpt"
    _name = "account.account"

    selection_value = [
        ("asset_receivable", "Receivable"),
        ("asset_cash", "Bank and Cash"),
        ("asset_current", "Current Assets"),
        ("asset_non_current", "Non-current Assets"),
        ("asset_prepayments", "Prepayments"),
        ("asset_fixed", "Fixed Assets"),
        ("liability_payable", "Payable"),
        ("liability_credit_card", "Credit Card"),
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Non-current Liabilities"),
        ("equity", "Equity"),
        ("equity_unaffected", "Current Year Earnings"),
        ("income", "Income"),
        ("income_other", "Other Income"),
        ("expense", "Expenses"),
        ("expense_depreciation", "Depreciation"),
        ("expense_direct_cost", "Cost of Revenue"),
        ("off_balance", "Off-Balance Sheet"),
        ("view", "View"),
    ]

    rpt_config_line_ids = fields.One2many('account.report.config.line', 'acc_id',
                                          string='FS Recommendation And Settings', copy=True, tracking=True)
    parent_rpt_config_line_ids = fields.One2many('parent.account.report.config.line', 'acc_id',
                                          string='Parent FS Recommendation', copy=True, tracking=True)

    allow_user_type_id = fields.Many2one('account.account.type', string='Allowed Account Type', tracking=True)
    account_type_allow = fields.Selection(selection_value, string='Allowed Type')

    parent_hierarchy = fields.Char(string="Parent Hierarchy", compute="_compute_parent_hierarchy", store=True)

    @api.onchange('parent_child_type')
    def _onchange_parent_child_type(self):
        if self.parent_child_type:
            if self.parent_child_type == 'parent':
                if not self.env.user.has_group('custom_financial_reports.group_coa_controller'):
                    raise UserError('Required parent creation access!')
                else:
                    self.account_type = 'view'

                return {'domain': {'parent_id': [('account_type','=','view'), ('child_parent_child_type', 'in', ['parent','both'])]},
                            'value': {'parent_id': None, 'code': None, 'name': None}} #,('allow_user_type_id','=',None)
            else:
                return {'domain': {'parent_id': [('account_type','=','view'), ('child_parent_child_type', 'in', ['child','both'])]},
                        'value': {'account_type': None, 'parent_id': None, 'code': None, 'name': None}}
        else:
            return {'domain': {'parent_id': [('account_type','=','view')]}, 'value': {'account_type': None, 'parent_id': None, 'code': None, 'name': None}}

    @api.onchange('parent_id')
    def _onchange_parent_id_dynamic(self):
        if self.parent_id:
            self.tag_ids = None

            parent_id = self.parent_id.id
            parent_configs = self.env['parent.account.report.config.line'].search([('acc_id', '=', parent_id)])
            if parent_configs:
                config_list = []
                for rec in parent_configs:
                    vals = {
                        'acc_id': rec.acc_id.id,
                        'fs_particular_id': rec.fs_particular_id.id if rec.fs_particular_id else None,
                        'rec_type': rec.rec_type,
                        'rec_title_id': rec.rec_title_id.id if rec.rec_title_id else None,
                        'rec_amt_type': rec.rec_amt_type,
                        'rec_sign': rec.rec_sign
                    }
                    config_list.append((0, 0, vals))

                if len(config_list)>0:
                    if self.parent_child_type == 'parent':
                        self.parent_rpt_config_line_ids = config_list
                    elif self.parent_child_type == 'child':
                        if len(self.rpt_config_line_ids) == 0:
                            self.rpt_config_line_ids = config_list
                        else:
                            pass
                            #self.rpt_config_line_ids = config_list

            #-------- assign Type
            if self.parent_child_type == 'parent':
                self.account_type = self.parent_id.account_type if self.parent_id.account_type else None
            else:
                self.account_type = self.parent_id.account_type_allow if self.parent_id.account_type_allow else None

            #------------- assign groups
            self.tag_ids = self.parent_id.tag_ids.ids if self.parent_id.tag_ids else None


    @api.depends('parent_id')
    def _compute_parent_hierarchy(self):
        for rec in self:
            hierarchy = ''
            first_p_obj = rec.parent_id
            if first_p_obj:
                hierarchy = str(first_p_obj.name)
                second_p_obj = first_p_obj.parent_id
                if second_p_obj:
                    hierarchy = str(second_p_obj.name) +' >> '+ hierarchy
                    third_p_obj = second_p_obj.parent_id
                    if third_p_obj:
                        hierarchy = str(third_p_obj.name) + ' >> ' + hierarchy
                        fourth_p_obj = third_p_obj.parent_id
                        if fourth_p_obj:
                            hierarchy = str(fourth_p_obj.name) + ' >> ' + hierarchy
                            fifth_p_obj = fourth_p_obj.parent_id
                            if fifth_p_obj:
                                hierarchy = str(fifth_p_obj.name) + ' >> ' + hierarchy
                                sixth_p_obj = fifth_p_obj.parent_id
                                if sixth_p_obj:
                                    hierarchy = str(sixth_p_obj.name) + ' >> ' + hierarchy
                                    seven_p_obj = sixth_p_obj.parent_id
                                    if seven_p_obj:
                                        hierarchy = str(seven_p_obj.name) + ' >> ' + hierarchy
                                        eight_p_obj = seven_p_obj.parent_id
                                        if eight_p_obj:
                                            hierarchy = str(eight_p_obj.name) + ' >> ' + hierarchy
                                            nine_p_obj = eight_p_obj.parent_id
                                            if nine_p_obj:
                                                hierarchy = str(nine_p_obj.name) + ' >> ' + hierarchy

            rec.parent_hierarchy = hierarchy

    # def unlink(self):
    #     for rec in self:
    #         child_objs = self.env['account.account'].search([('parent_id', '=', rec.id)], limit=1)
    #         if child_objs:
    #             raise UserError('This account has child account!')
    #     return super(AccountAccountInheritDynamicRpt, self).unlink()

    @api.model_create_multi
    def create(self, vals):
        #---------------
        res = super(AccountAccountInheritDynamicRpt, self).create(vals)
        for rec in res:
            # if rec.account_type != 'view':
            #     coa_reports_config = self.env['custom.common.settings'].search(
            #         [('key', '=', 'coa_reports_config'), ('value', '=', True)], limit=1)
            #     if coa_reports_config:
            #         if len(rec.rpt_config_line_ids) == 0:
            #             raise ValidationError("Account cannot be created without report configuration.")

            #------------
            if rec.parent_child_type == 'parent':
                if not self.env.user.has_group('custom_financial_reports.group_coa_controller'):
                    raise ValidationError('Required parent creation access!')

        return res

    def write(self, vals):
        res = super(AccountAccountInheritDynamicRpt, self).write(vals)
        if res:
            for rec in self:
                # if rec.account_type != 'view':
                #     coa_reports_config = self.env['custom.common.settings'].search(
                #         [('key', '=', 'coa_reports_config'), ('value', '=', True)], limit=1)
                #     if coa_reports_config:
                #         if len(rec.rpt_config_line_ids) == 0:
                #             raise ValidationError("Account cannot be created without report configuration.")

                # ------------
                if rec.parent_child_type == 'parent':
                    if not self.env.user.has_group('custom_financial_reports.group_coa_controller'):
                        raise ValidationError('Required parent creation access!')

        return res


class AccountReportConfigLine(models.Model):
    _name = 'account.report.config.line'
    #_inherit = ['mail.thread']

    _description = "Reports Recommendation And Settings"
    _order = "fs_particular_id, rec_title_id"

    acc_id = fields.Many2one('account.account', ondelete="cascade", string='Reports Recommendation & Settings')

    # Recommendation
    rec_type = fields.Selection([
        ('BL', 'Balance Sheet'),
        ('CF', 'Cash Flow'),
        ('EQ', 'Equity'),
        ('PL', 'Profit & Loss'),
        ('RP', 'Receipts & Payments')
    ], string='Recom.Report Type')
    fs_particular_id = fields.Many2one('acc.particular', ondelete='restrict', string='Recom.FS.Report')

    rec_title_id = fields.Many2one('acc.particular.line', ondelete="restrict", string='Recom.Title', domain=[('acc_particular_id.active', '=', True)])
    rec_amt_type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit'), ('blnc', 'Balance')], string='Recom.Amount Type')
    rec_sign = fields.Selection([('1', 'Plus'), ('-1', 'Minus')], string='Recom.Sign', default='1')

    # Settings
    conf_type = fields.Selection([
        ('BL', 'Balance Sheet'),
        ('CF', 'Cash Flow'),
        ('EQ', 'Equity'),
        ('PL', 'Profit & Loss'),
        ('RP', 'Receipts & Payments')
    ], string='Sett.Report Type')
    conf_fs_particular_id = fields.Many2one('acc.particular', ondelete='restrict', string='Sett.FS.Report')
    conf_title_id = fields.Many2one('acc.particular.line', ondelete="restrict", string='Sett.Title')
    conf_amt_type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit'), ('blnc', 'Balance')],
                                     string='Sett.Amount Type')
    conf_sign = fields.Selection([('1', 'Plus'), ('-1', 'Minus')], string='Sett.Sign')

    # @api.onchange('rec_type')
    # def _onchange_rec_type(self):
    #     return {'value': {'rec_title_id': None}}

    @api.onchange('fs_particular_id')
    def _onchange_fs_particular_id(self):
        return {'value': {'rec_title_id': None}, 'domain': {'rec_title_id': [('acc_particular_id', '=', self.fs_particular_id.id)]}}

    @api.constrains('rec_title_id')
    def _check_unique_code(self):
        for rec in self:
            if rec.rec_title_id:
                msg = 'Recommendation Title "%s" of this account' % rec.rec_title_id.name
                envobj = self.env['account.report.config.line']
                conditionlist = [('acc_id', '=', rec.acc_id.id), ('rec_title_id', '=', rec.rec_title_id.id)]

                # ----------
                commonList = [('id', '!=', self.id)]
                conditionList = conditionlist + commonList
                records = envobj.search(conditionList, limit=1)
                if records:
                    raise exceptions.ValidationError("'" + msg + "' already exists!")

    @api.model_create_multi
    def create(self, vals):
        res = super(AccountReportConfigLine, self).create(vals)
        for rec in res:
            if rec.acc_id.account_type != 'view':
                current_time = fields.datetime.now()
                acc_particular_line_details_obj = self.env['acc.particular.line.details']
                #acc_particular_line_details_id = acc_particular_line_details_obj.search([('account_id', '=', rec.acc_id.id), ('acc_particular_line_id.acc_particular_id.type', '=', rec.rec_type), ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
                acc_particular_line_details_id = acc_particular_line_details_obj.search([('account_id', '=', rec.acc_id.id), ('acc_particular_line_id.acc_particular_id', '=', rec.fs_particular_id.id), ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
                if not acc_particular_line_details_id:
                    acc_particular_line_details_obj.create({
                        'acc_particular_line_id': rec.rec_title_id.id,
                        'account_id': rec.acc_id.id,
                        'amt_type': rec.rec_amt_type,
                        'sign': rec.rec_sign
                    })

        return res

    def write(self, vals):
        res = super(AccountReportConfigLine, self).write(vals)
        if res:
            for rec in self:
                if rec.acc_id.account_type != 'view':
                    acc_particular_line_details_obj = self.env['acc.particular.line.details']
                    # acc_particular_line_details_id = acc_particular_line_details_obj.search(
                    #     [('account_id', '=', rec.acc_id.id),
                    #      ('acc_particular_line_id.acc_particular_id.type', '=', rec.rec_type),
                    #      ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)

                    acc_particular_line_details_id = acc_particular_line_details_obj.search(
                        [('account_id', '=', rec.acc_id.id),
                         ('acc_particular_line_id.acc_particular_id', '=', rec.fs_particular_id.id),
                         ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
                    if acc_particular_line_details_id:
                        acc_particular_line_details_id.acc_particular_line_id = rec.rec_title_id.id
                        acc_particular_line_details_id.account_id = rec.acc_id.id
                        acc_particular_line_details_id.amt_type = rec.rec_amt_type
                        acc_particular_line_details_id.sign = rec.rec_sign
        return res

    def unlink(self):
        for rec in self:
            if not self.env.context.get('account_rpt_config'):
                acc_particular_line_details_id = self.env['acc.particular.line.details'].search(
                    [('account_id', '=', rec.acc_id.id),
                     ('acc_particular_line_id.acc_particular_id', '=', rec.fs_particular_id.id),
                     ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)

                acc_particular_line_details_id.unlink()

            return super(AccountReportConfigLine, rec).unlink()


class ParentAccountReportConfigLine(models.Model):
    _name = 'parent.account.report.config.line'
    #_inherit = ['mail.thread']

    _description = "Parent Reports Recommendation And Settings"
    _order = "fs_particular_id, rec_title_id"

    acc_id = fields.Many2one('account.account', ondelete="cascade", string='Reports Recommendation')

    # Recommendation
    rec_type = fields.Selection([
        ('BL', 'Balance Sheet'),
        ('CF', 'Cash Flow'),
        ('EQ', 'Equity'),
        ('PL', 'Profit & Loss'),
        ('RP', 'Receipts & Payments')
    ], string='Recom.Report Type')
    fs_particular_id = fields.Many2one('acc.particular', ondelete='restrict', string='Recom.FS.Report')

    rec_title_id = fields.Many2one('acc.particular.line', ondelete="restrict", string='Recom.Title', domain=[('acc_particular_id.active', '=', True)])
    rec_amt_type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit'), ('blnc', 'Balance')], string='Recom.Amount Type')
    rec_sign = fields.Selection([('1', 'Plus'), ('-1', 'Minus')], string='Recom.Sign', default='1')

    # @api.onchange('rec_type')
    # def _onchange_rec_type(self):
    #     return {'value': {'rec_title_id': None}}

    @api.onchange('fs_particular_id')
    def _onchange_fs_particular_id(self):
        return {'value': {'rec_title_id': None},
                'domain': {'rec_title_id': [('acc_particular_id', '=', self.fs_particular_id.id)]}}

    @api.constrains('rec_title_id')
    def _check_unique_code(self):
        for rec in self:
            if rec.rec_title_id:
                msg = 'Parent Recommendation Title "%s" of this account' % rec.rec_title_id.name
                envobj = self.env['parent.account.report.config.line']
                conditionlist = [('acc_id', '=', rec.acc_id.id), ('rec_title_id', '=', rec.rec_title_id.id)]

                # ----------
                commonList = [('id', '!=', self.id)]
                conditionList = conditionlist + commonList
                records = envobj.search(conditionList, limit=1)
                if records:
                    raise exceptions.ValidationError("'" + msg + "' already exists!")



    # @api.model
    # def create(self, vals):
    #     res = super(AccountReportConfigLine, self).create(vals)
    #     for rec in res:
    #         if rec.acc_id.user_type_id.type != 'view':
    #             acc_particular_line_details_obj = self.env['acc.particular.line.details']
    #             acc_particular_line_details_id = acc_particular_line_details_obj.search([('account_id', '=', rec.acc_id.id), ('acc_particular_line_id.acc_particular_id.type', '=', rec.rec_type), ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
    #             if not acc_particular_line_details_id:
    #                 acc_particular_line_details_obj.create({
    #                     'acc_particular_line_id': rec.rec_title_id.id,
    #                     'account_id': rec.acc_id.id,
    #                     'amt_type': rec.rec_amt_type,
    #                     'sign': rec.rec_sign,
    #                 })
    #
    #     return res
    #
    # def write(self, vals):
    #     res = super(AccountReportConfigLine, self).write(vals)
    #     if res:
    #         for rec in self:
    #             if rec.acc_id.user_type_id.type != 'view':
    #                 acc_particular_line_details_obj = self.env['acc.particular.line.details']
    #                 acc_particular_line_details_id = acc_particular_line_details_obj.search(
    #                     [('account_id', '=', rec.acc_id.id),
    #                      ('acc_particular_line_id.acc_particular_id.type', '=', rec.rec_type),
    #                      ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
    #                 if acc_particular_line_details_id:
    #                     acc_particular_line_details_id.acc_particular_line_id = rec.rec_title_id.id
    #                     acc_particular_line_details_id.account_id = rec.acc_id.id
    #                     acc_particular_line_details_id.amt_type = rec.rec_amt_type
    #                     acc_particular_line_details_id.sign = rec.rec_sign
    #     return res
    #
    # def unlink(self):
    #     for rec in self:
    #         acc_particular_line_details_id = self.env['acc.particular.line.details'].search([('account_id', '=', rec.acc_id.id), ('acc_particular_line_id.acc_particular_id.type', '=', rec.rec_type), ('acc_particular_line_id', '=', rec.rec_title_id.id)], limit=1)
    #
    #         if not self.env.context.get('account_rpt_config'):
    #             acc_particular_line_details_id.unlink()
    #
    #         return super(AccountReportConfigLine, rec).unlink()
