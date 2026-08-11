from odoo import api, fields, models, _
from odoo.addons.helper import validator


class AccountParticular(models.Model):
    _name = 'acc.particular'
    _description = 'Account Particular'

    name = fields.Char(string='Name', default='_', copy=False)
    type = fields.Selection([
        ('BL', 'Balance Sheet'),
        ('CF', 'Cash Flow'),
        ('EQ', 'Equity'),
        ('PL', 'Profit & Loss'),
        ('RP', 'Receipts & Payments')
    ], string='Report Type')
    active = fields.Boolean(string='Active')
    acc_particular_line_ids = fields.One2many('acc.particular.line', 'acc_particular_id',
                                              string='Account Particular Line', copy=True)
    z_view_rule = fields.Selection([
        ('blank', 'Blank'),
        ('dash', 'Dash'),
    ], 'Zero View Rule', default='blank', help="Zero value print rule in report")
    usd_rate = fields.Float(string='USD Rate', default=1.00)

    fs_dept = fields.Selection([
        ('accounts', 'Accounts'),
        ('pf', 'PF')
    ], string='FS Department', default='accounts')

    profit_loss_id = fields.Many2one('acc.particular', string='Profit-Loss Report Config Ref.', domain="[('type', '=', 'PL')]", ondelete='cascade')
    rpt_title_name = fields.Char(string='Report Title Name', default='', copy=False)

    @api.depends('name', 'fs_dept')
    def name_get(self):
        return [(record.id, '{} [{}]'.format(record.name, dict(record._fields['fs_dept'].selection).get(record.fs_dept))) for record in self]

    @api.constrains('type')
    def _check_unique_account_particular_report_type(self):
        for rec in self:
            msg = '"%s" type report' % dict(self._fields['type'].selection).get(self.type)
            envobj = self.env['acc.particular']
            #conditionlist = [('type', '=', rec.type), ('fs_dept', '=', rec.fs_dept)]
            conditionlist = [('name', '=', rec.name), ('fs_dept', '=', rec.fs_dept)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    def action_map_accounts(self):
        report_type = self.type  # particular config type
        account_config_obj = self.env['account.report.config.line']
        particular_details_obj = self.env['acc.particular.line.details']
        fs_particular_id = self.id
        current_time = fields.datetime.now()

        for rec in self.acc_particular_line_ids:  # loop through particular lines
            title = rec.id
            if rec.value_type == 'dynamic':  # checks if particular line value type is dynamic or not
                account_objs = account_config_obj.sudo().search([('fs_particular_id', '=', fs_particular_id), ('rec_title_id', '=', title)])
                for acc_rec in account_objs:
                    part_det_obj = particular_details_obj.sudo().search([('acc_particular_line_id', '=', title), ('account_id', '=', acc_rec.acc_id.id)], limit=1)
                    if part_det_obj:
                        part_det_obj.amt_type = acc_rec.rec_amt_type
                        part_det_obj.sign = acc_rec.rec_sign
                        part_det_obj.last_map_time = current_time
                    else:
                        particular_details_obj.create({
                            'acc_particular_line_id': title,
                            'account_id': acc_rec.acc_id.id,
                            'amt_type': acc_rec.rec_amt_type,
                            'sign': acc_rec.rec_sign,
                            'last_map_time': current_time
                        })
                    #---------
                    acc_rec.conf_type = report_type
                    acc_rec.conf_fs_particular_id = fs_particular_id
                    acc_rec.conf_title_id = title
                    acc_rec.conf_amt_type = acc_rec.rec_amt_type
                    acc_rec.conf_sign = acc_rec.rec_sign

                # extra_part_det_obj = particular_details_obj.sudo().search(
                #         [('acc_particular_line_id', '=', title), ('account_id', '=', acc_rec.acc_id.id)], limit=1)

            else:
                continue
        return True

    # def action_map_accounts(self):
    #     report_type = self.type  # particular config type
    #     for rec in self.acc_particular_line_ids:  # loop through particular lines
    #         title = rec.id
    #         if rec.value_type == 'dynamic':  # checks if particular line value type is dynamic or not
    #             for rec2 in rec.acc_particular_line_details_ids:  # loop through line account details
    #                 amount_type = rec2.amt_type
    #                 sign = rec2.sign
    #                 if rec2.account_id.rpt_config_line_ids:
    #                     for rec3 in rec2.account_id.rpt_config_line_ids:  # loop through acc particular recommended line
    #                         # if recommended report type and title exists then update
    #                         if rec3.rec_type == report_type and rec3.rec_title_id.id == title:
    #                             rec3.conf_type = report_type
    #                             rec3.conf_title_id = title
    #                             rec3.conf_amt_type = amount_type
    #                             rec3.conf_sign = sign
    #                             break
    #                         # if report type and title already updated
    #                         elif rec3.conf_type == report_type and rec3.conf_title_id.id == title:
    #                             break
    #                 else:
    #                     # create if recommended report type and title not exists
    #                     vals = {
    #                         'conf_type': report_type,
    #                         'conf_title_id': title,
    #                         'conf_amt_type': amount_type,
    #                         'conf_sign': sign
    #                     }
    #                     rec2.account_id.rpt_config_line_ids = [(0, 0, vals)]
    #         else:
    #             continue
    #     return True


class AccountParticularLine(models.Model):
    _name = 'acc.particular.line'
    _description = 'Account Particular Line'
    _order = 'code asc'

    acc_particular_id = fields.Many2one('acc.particular', ondelete='cascade')
    acc_particular_line_details_ids = fields.One2many('acc.particular.line.details', 'acc_particular_line_id',
                                                      string='Account Particular Line Details', copy=True)
    name = fields.Char(string='Name')
    code = fields.Selection([
        ('BL01', 'BL01'), ('BL02', 'BL02'), ('BL03', 'BL03'), ('BL04', 'BL04'), ('BL05', 'BL05'), ('BL06', 'BL06'),
        ('BL07', 'BL07'), ('BL08', 'BL08'), ('BL09', 'BL09'), ('BL10', 'BL10'), ('BL11', 'BL11'), ('BL12', 'BL12'),
        ('BL13', 'BL13'), ('BL14', 'BL14'), ('BL15', 'BL15'), ('BL16', 'BL16'), ('BL17', 'BL17'), ('BL18', 'BL18'),
        ('BL19', 'BL19'), ('BL20', 'BL20'), ('BL21', 'BL21'), ('BL22', 'BL22'), ('BL23', 'BL23'), ('BL24', 'BL24'),
        ('BL25', 'BL25'), ('BL26', 'BL26'), ('BL27', 'BL27'), ('BL28', 'BL28'), ('BL29', 'BL29'), ('BL30', 'BL30'),
        ('BL31', 'BL31'), ('BL32', 'BL32'), ('BL33', 'BL33'), ('BL34', 'BL34'), ('BL35', 'BL35'), ('BL36', 'BL36'),
        ('BL37', 'BL37'), ('BL38', 'BL38'), ('BL39', 'BL39'), ('BL40', 'BL40'), ('BL41', 'BL41'), ('BL42', 'BL42'),
        ('BL43', 'BL43'), ('BL44', 'BL44'), ('BL45', 'BL45'), ('BL46', 'BL46'), ('BL47', 'BL47'), ('BL48', 'BL48'),
        ('BL49', 'BL49'), ('BL50', 'BL50'),
        ('PL01', 'PL01'), ('PL02', 'PL02'), ('PL03', 'PL03'), ('PL04', 'PL04'), ('PL05', 'PL05'), ('PL06', 'PL06'),
        ('PL07', 'PL07'), ('PL08', 'PL08'), ('PL09', 'PL09'), ('PL10', 'PL10'), ('PL11', 'PL11'), ('PL12', 'PL12'),
        ('PL13', 'PL13'), ('PL14', 'PL14'), ('PL15', 'PL15'), ('PL16', 'PL16'), ('PL17', 'PL17'), ('PL18', 'PL18'),
        ('PL19', 'PL19'), ('PL20', 'PL20'), ('PL21', 'PL21'), ('PL22', 'PL22'), ('PL23', 'PL23'), ('PL24', 'PL24'),
        ('PL25', 'PL25'), ('PL26', 'PL26'), ('PL27', 'PL27'), ('PL28', 'PL28'), ('PL29', 'PL29'), ('PL30', 'PL30'),
        ('PL31', 'PL31'), ('PL32', 'PL32'), ('PL33', 'PL33'), ('PL34', 'PL34'), ('PL35', 'PL35'), ('PL36', 'PL36'),
        ('PL37', 'PL37'), ('PL38', 'PL38'), ('PL39', 'PL39'), ('PL40', 'PL40'), ('PL41', 'PL41'), ('PL42', 'PL42'),
        ('PL43', 'PL43'), ('PL44', 'PL44'), ('PL45', 'PL45'), ('PL46', 'PL46'), ('PL47', 'PL47'), ('PL48', 'PL48'),
        ('PL49', 'PL49'), ('PL50', 'PL50'),
        ('CF01', 'CF01'), ('CF02', 'CF02'), ('CF03', 'CF03'), ('CF04', 'CF04'), ('CF05', 'CF05'), ('CF06', 'CF06'),
        ('CF07', 'CF07'), ('CF08', 'CF08'), ('CF09', 'CF09'), ('CF10', 'CF10'), ('CF11', 'CF11'), ('CF12', 'CF12'),
        ('CF13', 'CF13'), ('CF14', 'CF14'), ('CF15', 'CF15'), ('CF16', 'CF16'), ('CF17', 'CF17'), ('CF18', 'CF18'),
        ('CF19', 'CF19'), ('CF20', 'CF20'), ('CF21', 'CF21'), ('CF22', 'CF22'), ('CF23', 'CF23'), ('CF24', 'CF24'),
        ('CF25', 'CF25'), ('CF26', 'CF26'), ('CF27', 'CF27'), ('CF28', 'CF28'), ('CF29', 'CF29'), ('CF30', 'CF30'),
        ('CF31', 'CF31'), ('CF32', 'CF32'), ('CF33', 'CF33'), ('CF34', 'CF34'), ('CF35', 'CF35'), ('CF36', 'CF36'),
        ('CF37', 'CF37'), ('CF38', 'CF38'), ('CF39', 'CF39'), ('CF40', 'CF40'), ('CF41', 'CF41'), ('CF42', 'CF42'),
        ('CF43', 'CF43'), ('CF44', 'CF44'), ('CF45', 'CF45'), ('CF46', 'CF46'), ('CF47', 'CF47'), ('CF48', 'CF48'),
        ('CF49', 'CF49'), ('CF50', 'CF50'),
        ('RP01', 'RP01'), ('RP02', 'RP02'), ('RP03', 'RP03'), ('RP04', 'RP04'), ('RP05', 'RP05'), ('RP06', 'RP06'),
        ('RP07', 'RP07'), ('RP08', 'RP08'), ('RP09', 'RP09'), ('RP10', 'RP10'), ('RP11', 'RP11'), ('RP12', 'RP12'),
        ('RP13', 'RP13'), ('RP14', 'RP14'), ('RP15', 'RP15'), ('RP16', 'RP16'), ('RP17', 'RP17'), ('RP18', 'RP18'),
        ('RP19', 'RP19'), ('RP20', 'RP20'), ('RP21', 'RP21'), ('RP22', 'RP22'), ('RP23', 'RP23'), ('RP24', 'RP24'),
        ('RP25', 'RP25'), ('RP26', 'RP26'), ('RP27', 'RP27'), ('RP28', 'RP28'), ('RP29', 'RP29'), ('RP30', 'RP30'),
        ('RP31', 'RP31'), ('RP32', 'RP32'), ('RP33', 'RP33'), ('RP34', 'RP34'), ('RP35', 'RP35'), ('RP36', 'RP36'),
        ('RP37', 'RP37'), ('RP38', 'RP38'), ('RP39', 'RP39'), ('RP40', 'RP40'), ('RP41', 'RP41'), ('RP42', 'RP42'),
        ('RP43', 'RP43'), ('RP44', 'RP44'), ('RP45', 'RP45'), ('RP46', 'RP46'), ('RP47', 'RP47'), ('RP48', 'RP48'),
        ('RP49', 'RP49'), ('RP50', 'RP50'),
    ], string='Code')

    # ('EQ01', 'EQ01'), ('EQ02', 'EQ02'), ('EQ03', 'EQ03'), ('EQ04', 'EQ04'), ('EQ05', 'EQ05'), ('EQ06', 'EQ06'),
    # ('EQ07', 'EQ07'), ('EQ08', 'EQ08'), ('EQ09', 'EQ09'), ('EQ10', 'EQ10'), ('EQ11', 'EQ11'), ('EQ12', 'EQ12'),
    # ('EQ13', 'EQ13'), ('EQ14', 'EQ14'), ('EQ15', 'EQ15'), ('EQ16', 'EQ16'), ('EQ17', 'EQ17'), ('EQ18', 'EQ18'),
    # ('EQ19', 'EQ19'), ('EQ20', 'EQ20'), ('EQ21', 'EQ21'), ('EQ22', 'EQ22'), ('EQ23', 'EQ23'), ('EQ24', 'EQ24'),
    # ('EQ25', 'EQ25')

    sequence = fields.Integer(string='Sequence', default=1)
    include_op_balance = fields.Boolean(string='Include Opening')
    notes = fields.Char('Notes')
    value_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('dynamic', 'Dynamic'),
    ], string='Value Type', default='dynamic')
    fixed_amt = fields.Float(string='Fixed Amount', default=0)
    fixed_cmp_amt = fields.Float(string='Fixed Comparison Amount', default=0)

    def action_acc_particular_line(self):
        action_ctx = dict(self.env.context)
        view_id = self.env.ref('dynamic_accounts_report.view_acc_particular_line_form').id
        return {
            'name': _('Account Particular Line Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'acc.particular.line',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': action_ctx}


class AccountParticularLineDetails(models.Model):
    _name = 'acc.particular.line.details'
    _description = 'Account Particular Line Details'

    acc_particular_line_id = fields.Many2one('acc.particular.line', ondelete='cascade')
    account_id = fields.Many2one('account.account', 'Chart of Accounts',
                                 required=True,
                                 ondelete='cascade')
    amt_type = fields.Selection([
        ('dr', 'Debit'), ('cr', 'Credit'), ('blnc', 'Balance')
    ], string='Amount Type')
    sign = fields.Selection([('1', 'Plus'), ('-1', 'Minus')], string='Sign', default='1')

    last_map_time = fields.Datetime('Map Time')

    _sql_constraints = [('unique_account_id', 'UNIQUE(acc_particular_line_id, account_id)',
                         'Warning! You cannot add the same account twice or more.')]

    def unlink(self):
        for rec in self:
            account_report_config_line_id = self.env['account.report.config.line'].search([('acc_id', '=', rec.account_id.id), ('conf_title_id', '=', rec.acc_particular_line_id.id)], limit=1)
            account_report_config_line_id.with_context(account_rpt_config=True).unlink()
        return super(AccountParticularLineDetails, self).unlink()
