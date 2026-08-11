from odoo import api, fields, models
from odoo.tools.misc import get_lang


class CashFlow(models.Model):
    """Inherits the account.account model to add additional functionality and
     fields to the account"""
    _inherit = 'account.account'

    parent_child_type = fields.Selection([
        ('parent', 'Parent'),
        ('child', 'Child')
    ], string='Parent/Child', default='child', tracking=True)
    user_type_id_type = fields.Selection(related='account_type', string="User Account Type")
    child_parent_child_type = fields.Selection([
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('both', 'Parent/Child'),
        ('none', 'None'),
    ], string='Child- Parent/Child', default='none')
    child_code_digit = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4')
    ], string='Child- Code Digits', default='1')
    is_po_discount = fields.Boolean(string='Purchase Order Discount', tracking=True)



class AccountCommonReport(models.Model):
    """Inherits the Account report model to add special fields and functions"""
    _inherit = "account.report"
    _description = "Account Common Report"

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='List of Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]")
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves',
                                   required=True, default='posted')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Onchange function based on the company and updated the journals"""
        if self.company_id:
            self.journal_ids = self.env['account.journal'].search(
                [('company_id', '=', self.company_id.id)])
        else:
            self.journal_ids = self.env['account.journal'].search([])

    def _build_contexts(self, data):
        """Builds the context information for the given data"""
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        return result

    def _print_report(self, data):
        """Raise an error if the report comes checked """
        raise NotImplementedError()

    def check_report(self):
        """Function to check if the report comes active models and related
        values"""
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)


class AccountCommonJournalReport(models.TransientModel):
    """Model used for creating the common journal report"""
    _name = 'account.common.journal.report'
    _description = 'Common Journal Report'
    _inherit = "account.report"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_common_journal_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_common_journal_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    amount_currency = fields.Boolean(
        'With Currency',
        help="Print Report with the currency column if the currency differs "
             "from the company currency.")
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves',
                                   required=True, default='posted')

    def pre_print_report(self, data):
        """Pre-print the given data and that updates the amount
        amount_currency value"""
        data['form'].update({'amount_currency': self.amount_currency})
        return data

    def check_report(self):
        """Function to check if the report comes active models and related
                values"""
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def _build_contexts(self, data):
        """Builds the context information for the given data"""
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        return result
