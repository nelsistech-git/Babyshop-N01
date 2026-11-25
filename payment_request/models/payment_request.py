# -*- coding: utf-8 -*-
import base64
import html
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from .res_company import amount_to_words_bdt

PAYMENT_MODE_SELECTION = [
    ('beftn', 'BEFTN'),
    ('rtgs', 'RTGS'),
    ('ac_payee_cheque', 'A/C Payee Cheque'),
    ('cash_cheque', 'Cash Cheque'),
    ('cash', 'Cash'),
    ('bank', 'Bank Transfer'),
    ('pay_order', 'Pay Order'),
]


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Payment Requisition'
    _order = 'request_date desc, id desc'

    name = fields.Char(string='Req. No.', required=True, copy=False, readonly=True, default='New')
    request_date = fields.Date(string='Req. Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')

    prepared_by_id = fields.Many2one('res.users', string='Prepared By', default=lambda self: self.env.user, tracking=True)
    lm_approved_by_id = fields.Many2one('res.users', string='Line Manager Approved By', readonly=True, copy=False, tracking=True)
    lm_approved_date = fields.Date(string='Line Manager Approved Date', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False, tracking=True,
                                     help='Whoever gave the final sign-off - Head of Finance & Accounts, '
                                          'or Executive (CEO/MD/Director) when the amount required it.')
    approved_date = fields.Date(string='Approved Date', readonly=True, copy=False)
    final_approver_role = fields.Selection([
        ('hof', 'Head of Finance & Accounts'),
        ('exec', 'Executive (CEO/MD/Director)'),
    ], string='Final Approval Given By', readonly=True, copy=False,
        help='Which role gave the final sign-off above - Head of Finance & Accounts (amount within the '
             'Executive Approval Threshold) or Executive/CEO/MD/Director (amount exceeded it).')
    bank_forward_date = fields.Date(string='Bank Forward Date', readonly=True, copy=False)

    # LEGACY (pre 17.0.1.3.0): the debit account used to be chosen once per
    # request. It is now chosen per LINE (see PaymentRequestLine.own_bank_id /
    # own_bank_branch_id). These two are kept only so the migration can copy
    # old values onto the lines; they are no longer shown or used.
    own_bank_id = fields.Many2one('res.partner.bank', string='Debit Account (legacy)')
    own_bank_branch = fields.Char(string='Debit Account Branch (legacy)')

    beftn_ref = fields.Char(string='BEFTN Reference No.', readonly=True, copy=False,
                            help='Assigned once, the first time the BEFTN letter is printed or the '
                                 'request is marked forwarded - shared by every BEFTN line in this request.')

    vds_certificate_no = fields.Char(string='Mushak 6.6 Certificate No.', readonly=True, copy=False,
                                     help='Assigned once, the first time the Mushak 6.6 VDS Certificate '
                                          'is printed for this request.')
    vds_certificate_date = fields.Date(string='Mushak 6.6 Issue Date', readonly=True, copy=False)
    challan_no = fields.Char(string='Challan No.', copy=False, tracking=True,
                             help='Treasury challan number of the VDS deposit - printed on the Mushak 6.6 certificate.')
    challan_date = fields.Date(string='Challan Date', copy=False, tracking=True,
                               help='Treasury challan date - printed on the Mushak 6.6 certificate.')

    commercial_tt_id = fields.Many2one(
        'commercial.tt', string='Source TT Document', readonly=True, copy=False,
        help='Set when this Payment Request was auto-created by forwarding a TT document to Accounting.')

    line_ids = fields.One2many('payment.request.line', 'request_id', string='Lines')

    total_bill_amount = fields.Monetary(string='Total Bill Amount', currency_field='currency_id',
                                        compute='_compute_totals', store=True)
    total_deduction = fields.Monetary(string='Total Deduction', currency_field='currency_id',
                                      compute='_compute_totals', store=True)
    total_wht = fields.Monetary(string='Total WHT', currency_field='currency_id',
                                compute='_compute_totals', store=True)
    total_whvat = fields.Monetary(string='Total WHVAT', currency_field='currency_id',
                                  compute='_compute_totals', store=True)
    total_net_payment = fields.Monetary(string='Total Net Payment', currency_field='currency_id',
                                        compute='_compute_totals', store=True)

    has_rtgs_lines = fields.Boolean(compute='_compute_has_lines')
    has_beftn_lines = fields.Boolean(compute='_compute_has_lines')
    has_vat_lines = fields.Boolean(compute='_compute_has_lines',
                                   help='True when at least one line has WHVAT (Tk.) > 0, i.e. there is '
                                        'something to certify on a Mushak 6.6 VDS Certificate.')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('lm_approved', 'Line Manager Approval'),
        ('approved', 'Approved'),
        ('bank_forwarded', 'Forwarded to Bank'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    reject_reason = fields.Text(string='Rejection Reason')

    # ---------------------------------------------------------------
    # Amount-based Executive routing - same shared "Executive Approval
    # Threshold" (Settings > Purchase - Vendor PI, default Tk 250,000) and
    # the same Line Manager / Head of Finance & Accounts / Executive
    # (CEO/MD/Director) groups used by Vendor Onboarding (product_vendor_
    # details) and Purchase Orders (purchase_vendor_pi), so one person's
    # role assignment covers all three approval chains. Below the
    # threshold the Head of Finance & Accounts gives the final approval;
    # above it, Executive approval is required INSTEAD (not in addition -
    # see the 2026-09-13 P2P workflow diagram, which shows this as an
    # either/or branch for Payment specifically, unlike the PO chain
    # where Executive approval is an extra step on top of Head of Finance).
    # ---------------------------------------------------------------
    x_requires_exec_approval = fields.Boolean(
        string='Requires Executive Approval', compute='_compute_requires_exec_approval', store=True,
        help='True when Total Net Payment exceeds Settings > Purchase - Vendor PI > Executive '
             'Approval Threshold. When true, Executive (CEO/MD/Director) approval replaces Head '
             'of Finance & Accounts approval as the final sign-off step.')

    @api.depends('total_net_payment', 'company_id.pvpi_exec_approval_threshold')
    def _compute_requires_exec_approval(self):
        for rec in self:
            threshold = rec.company_id.pvpi_exec_approval_threshold or 0.0
            rec.x_requires_exec_approval = threshold > 0 and rec.total_net_payment > threshold

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.request') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.bill_amount', 'line_ids.deduction_amount',
                 'line_ids.wht_amount', 'line_ids.whvat_amount', 'line_ids.net_payment')
    def _compute_totals(self):
        for rec in self:
            rec.total_bill_amount = sum(rec.line_ids.mapped('bill_amount'))
            rec.total_deduction = sum(rec.line_ids.mapped('deduction_amount'))
            rec.total_wht = sum(rec.line_ids.mapped('wht_amount'))
            rec.total_whvat = sum(rec.line_ids.mapped('whvat_amount'))
            rec.total_net_payment = sum(rec.line_ids.mapped('net_payment'))

    @api.depends('line_ids.payment_mode', 'line_ids.whvat_amount')
    def _compute_has_lines(self):
        for rec in self:
            rec.has_rtgs_lines = bool(rec.line_ids.filtered(lambda l: l.payment_mode == 'rtgs'))
            rec.has_beftn_lines = bool(rec.line_ids.filtered(lambda l: l.payment_mode == 'beftn'))
            rec.has_vat_lines = bool(rec.line_ids.filtered(lambda l: l.whvat_amount > 0))

    @api.constrains('line_ids')
    def _check_has_lines(self):
        for rec in self:
            if rec.state != 'draft' and not rec.line_ids:
                raise ValidationError('A Payment Request cannot be moved forward with no lines.')

    # ---------------------------------------------------------------
    # Approval chain: Draft -> Line Manager Approval -> Approved (by Head
    # of Finance & Accounts, or by Executive/CEO/MD/Director instead when
    # Total Net Payment exceeds the Executive Approval Threshold).
    # Reuses the same groups as product_vendor_details / purchase_vendor_pi.
    # Administrators (base.group_system) can always act, as a fallback -
    # same convention as those two modules.
    # ---------------------------------------------------------------
    def _is_admin_or_in_group(self, group_xmlid):
        user = self.env.user
        return user.has_group('base.group_system') or user.has_group(group_xmlid)

    def action_lm_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only a Draft request can receive Line Manager approval.')
            if not rec.line_ids:
                raise UserError('Add at least one line before submitting for Line Manager approval.')
            if not rec._is_admin_or_in_group('product_vendor_details.group_vendor_line_manager'):
                raise UserError('You are not a Line Manager approver.')
            rec.write({'state': 'lm_approved', 'lm_approved_by_id': self.env.user.id,
                      'lm_approved_date': fields.Date.context_today(self)})

    def action_hof_approve(self):
        for rec in self:
            if rec.state != 'lm_approved':
                raise UserError('Only a Line-Manager-Approved request can receive Head of Finance '
                                '& Accounts approval.')
            if rec.x_requires_exec_approval:
                raise UserError('This request exceeds the Executive Approval Threshold - it needs '
                                'Executive (CEO/MD/Director) approval instead.')
            if not rec._is_admin_or_in_group('product_vendor_details.group_vendor_hof'):
                raise UserError('You are not a Head of Finance & Accounts approver.')
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id,
                      'approved_date': fields.Date.context_today(self), 'final_approver_role': 'hof'})

    def action_exec_approve(self):
        for rec in self:
            if rec.state != 'lm_approved':
                raise UserError('Only a Line-Manager-Approved request can receive Executive approval.')
            if not rec.x_requires_exec_approval:
                raise UserError('This request is below the Executive Approval Threshold - no '
                                'CEO/MD/Director approval is required; use Head of Finance & '
                                'Accounts Approval instead.')
            if not rec._is_admin_or_in_group('purchase_vendor_pi.group_po_executive'):
                raise UserError('You are not an Executive (CEO/MD/Director) approver.')
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id,
                      'approved_date': fields.Date.context_today(self), 'final_approver_role': 'exec'})

    def action_reject(self):
        for rec in self:
            if rec.state in ('bank_forwarded', 'paid', 'cancelled'):
                raise UserError('Cannot reject a request that has already been forwarded to the bank / paid.')
            rec.state = 'rejected'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state in ('bank_forwarded', 'paid'):
                raise UserError('Cannot reset to Draft once forwarded to the bank / paid.')
            rec.write({'state': 'draft', 'lm_approved_by_id': False, 'lm_approved_date': False,
                      'approved_by_id': False, 'approved_date': False, 'final_approver_role': False,
                      'reject_reason': False})

    def action_cancel(self):
        for rec in self:
            if rec.state in ('bank_forwarded', 'paid'):
                raise UserError('Cannot cancel a request that has already been forwarded to the bank / paid.')
            rec.state = 'cancelled'

    # ---------------------------------------------------------------
    # Bank forwarding - RTGS (one per line) / BEFTN (one consolidated
    # letter per request, all its BEFTN lines sharing one Reference No.).
    # ---------------------------------------------------------------
    def _ensure_beftn_ref(self):
        self.ensure_one()
        if not self.beftn_ref and self.line_ids.filtered(lambda l: l.payment_mode == 'beftn'):
            self.beftn_ref = self.env['ir.sequence'].next_by_code('payment.request.beftn.ref') or '/'
        return self.beftn_ref

    def _check_debit_account(self, lines):
        """RTGS / BEFTN letters need the Debit Account (Our Bank) on every line."""
        missing = lines.filtered(lambda l: not l.own_bank_id)
        if missing:
            raise UserError('Select the "Debit Account (Our Bank)" on these lines first:\n- %s'
                            % '\n- '.join(missing.mapped(lambda l: l.partner_id.name or '(no vendor)')))

    def action_print_requisition(self):
        """Internal Payment Requisition form (the 'Payment_Request_Form' layout) - any state."""
        self.ensure_one()
        return self.env.ref('payment_request.action_report_requisition').report_action(self)

    def _check_can_print_rtgs(self):
        for rec in self:
            if rec.state not in ('approved', 'bank_forwarded', 'paid'):
                raise UserError('Approve the request before printing bank letters.')
            lines = rec.line_ids.filtered(lambda l: l.payment_mode == 'rtgs')
            if not lines:
                raise UserError('No lines with Payment Mode = RTGS on %s.' % rec.name)
            rec._check_debit_account(lines)

    def _check_can_print_beftn(self):
        for rec in self:
            if rec.state not in ('approved', 'bank_forwarded', 'paid'):
                raise UserError('Approve the request before printing bank letters.')
            lines = rec.line_ids.filtered(lambda l: l.payment_mode == 'beftn')
            if not lines:
                raise UserError('No lines with Payment Mode = BEFTN on %s.' % rec.name)
            rec._check_debit_account(lines)

    def action_print_rtgs(self):
        self.ensure_one()
        self._check_can_print_rtgs()
        return self.env.ref('payment_request.action_report_rtgs').report_action(self)

    def action_print_beftn(self):
        self.ensure_one()
        self._check_can_print_beftn()
        self._ensure_beftn_ref()
        return self.env.ref('payment_request.action_report_beftn').report_action(self)

    # ---------------------------------------------------------------
    # Mushak 6.6 VDS (VAT Deducted at Source) Certificate - one certificate
    # per Payment Request, listing every line with WHVAT (Tk.) > 0, under
    # one Certificate No. assigned (like beftn_ref above) the first time
    # it's printed and then kept fixed for this request.
    # ---------------------------------------------------------------
    def _ensure_vds_certificate(self):
        """One certificate (own running No.) per supplier that has WHVAT > 0.
        The number is stored on that supplier's lines; the request keeps the list."""
        self.ensure_one()
        seq = self.env['ir.sequence']
        numbers = []
        vat_lines = self.line_ids.filtered(lambda l: l.whvat_amount > 0)
        for group in vat_lines.grouped(lambda l: l.partner_id.id).values():
            no = group.filtered('vds_certificate_no')[:1].vds_certificate_no
            if not no:
                no = seq.next_by_code('payment.request.vds.certificate') or '/'
            group.filtered(lambda l: not l.vds_certificate_no).write({'vds_certificate_no': no})
            numbers.append(no)
        if not self.vds_certificate_no:
            self.write({'vds_certificate_no': ', '.join(numbers),
                        'vds_certificate_date': fields.Date.context_today(self)})
        return self.vds_certificate_no

    def _check_can_print_mushak66(self):
        for rec in self:
            if not rec.vds_certificate_no:
                raise UserError('Issue Mushak 6.6 first (click "Issue 6.6"), then print it.')
            if not rec.line_ids.filtered(lambda l: l.whvat_amount > 0):
                raise UserError('No lines with WHVAT (Tk.) > 0 on %s - nothing to certify.' % rec.name)

    def action_print_mushak66(self):
        """Prints one certificate per supplier, each in 2 identical copies, each on its own page."""
        self.ensure_one()
        self._check_can_print_mushak66()
        return self.env.ref('payment_request.action_report_mushak66').report_action(self)

    def action_issue_mushak66(self):
        """Available once the request is Paid. Assigns a Certificate No. per supplier (once)
        and reloads the form - it does NOT print."""
        self.ensure_one()
        if self.state != 'paid':
            raise UserError('Mushak 6.6 can be issued only after the request is Paid.')
        vat_lines = self.line_ids.filtered(lambda l: l.whvat_amount > 0)
        if not vat_lines:
            raise UserError('No line has WHVAT (Tk.) greater than 0 - there is nothing to certify on a '
                            'Mushak 6.6. Add WHVAT on the line(s) first.')
        if not self.challan_no or not self.challan_date:
            raise UserError('Enter the Challan No. and Challan Date (treasury deposit) before issuing Mushak 6.6.')
        missing = vat_lines.filtered(lambda l: not l.vat_challan_no or not l.vat_challan_date)
        if missing:
            raise UserError('VAT Challan No / Date is missing for:\n- %s\n\nEnter it on the Vendor Bill '
                            '(Accounting > Vendors > Bills > "VAT Challan No / Date") - it syncs here '
                            'automatically.' % '\n- '.join(missing.mapped(lambda l: l.partner_id.name or '(no vendor)')))
        self._ensure_vds_certificate()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_mark_forwarded(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError('Only an Approved request can be marked Forwarded to Bank.')
            rec._ensure_beftn_ref()
            rec.write({'state': 'bank_forwarded', 'bank_forward_date': fields.Date.context_today(self)})

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'bank_forwarded':
                raise UserError('Only a request already Forwarded to Bank can be marked Paid.')
            # The payment is posted in Accounting from here - nobody has to open the bill and press
            # "Register Payment". Everything runs in one transaction: if one bill cannot be posted
            # (missing configuration, ...) the request stays 'Forwarded to Bank'.
            rec.action_create_vendor_payments()
            rec.state = 'paid'

    def action_create_vendor_payments(self):
        """Post the vendor payment of every line that has a Vendor Bill - exactly once per line."""
        for rec in self:
            if rec.state not in ('approved', 'bank_forwarded', 'paid'):
                raise UserError('Approve the request before posting vendor payments.')
            skipped = []
            for line in rec.line_ids.filtered(lambda l: l.invoice_id and not l.payment_move_id):
                if line.invoice_id.payment_state in ('paid', 'in_payment', 'reversed'):
                    # already settled by another route: never pay the same bill twice
                    skipped.append(line.invoice_id.name)
                    continue
                line.action_create_vendor_payment()
            if skipped:
                rec.message_post(body='Vendor Bill(s) %s were already paid in Accounting, so no second '
                                      'payment entry was created.' % ', '.join(skipped))


    @api.model
    def _beftn_letterhead_uri(self, part):
        """Data-URI of the company letterhead (Letter Head Pad) header / footer image used on the BEFTN letter."""
        with tools.file_open('payment_request/static/src/img/beftn_%s.png' % part, 'rb') as f:
            return 'data:image/png;base64,%s' % base64.b64encode(f.read()).decode()


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'
    _description = 'Payment Requisition Line'
    _order = 'sequence, id'

    request_id = fields.Many2one('payment.request', string='Payment Request', required=True, ondelete='cascade')
    request_state = fields.Selection(related='request_id.state', string='Request Status', store=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related='request_id.company_id', store=True)
    currency_id = fields.Many2one(related='request_id.currency_id', string='Currency')

    partner_id = fields.Many2one('res.partner', string='Beneficiary / Vendor / Party', required=True)
    invoice_id = fields.Many2one(
        'account.move', string='Vendor Bill', domain=lambda self: [
            ('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'reversed'))],
        help='Optional: pick the posted Vendor Bill this payment settles - pre-fills the amount and '
             'lets "Create Vendor Payment" post/reconcile the accounting entry automatically.')
    vendor_bin = fields.Char(
        string='Vendor BIN', copy=True,
        help='Vendor\'s BIN. Filled automatically from the vendor\'s Contact (Tax ID) when the vendor is '
             'selected, but you can edit it on this line. Printed on the Mushak 6.6 VDS Certificate and '
             'the RTGS application.')
    invoice_ref = fields.Char(string='Invoice Ref.')
    vat_challan_no = fields.Char(
        string='VAT Challan No', compute='_compute_vat_challan', store=True, readonly=False, copy=False,
        help='Synced from the Vendor Bill (VAT Challan No). Editable only when no Vendor Bill is linked. '
             'Printed on Mushak 6.6 under সংশ্লিষ্ট কর চালানপত্র - নম্বর.')
    vat_challan_date = fields.Date(
        string='VAT Challan Date', compute='_compute_vat_challan', store=True, readonly=False, copy=False,
        help='Synced from the Vendor Bill (VAT Challan Date). Printed on Mushak 6.6 under '
             'সংশ্লিষ্ট কর চালানপত্র - ইস্যুর তারিখ.')
    vds_certificate_no = fields.Char(string='Mushak 6.6 Cert. No.', readonly=True, copy=False,
                                     help='Certificate number of this supplier\'s Mushak 6.6.')
    invoice_date = fields.Date(string='Invoice Date')
    due_date = fields.Date(
        string='Due Date', compute='_compute_due_date', store=True, readonly=False, copy=False,
        help="Payment due date. Taken from the Vendor Bill's Due Date (Calculated) when a bill is "
             "linked - so it follows the bill's Bill Date + Payment Terms - and editable on lines "
             "without a bill (for example an Expense).")

    bill_amount = fields.Monetary(string='Bill Amount', currency_field='currency_id', required=True)
    deduction_amount = fields.Monetary(string='Deduction / (Adv. Adjustment)', currency_field='currency_id')
    wht_amount = fields.Monetary(string='WHT (Tk.)', currency_field='currency_id',
                                 help='Withholding Tax / TDS deducted from this payment.')
    whvat_amount = fields.Monetary(string='WHVAT (Tk.)', currency_field='currency_id',
                                   help='Withholding VAT / VDS deducted from this payment - printed as '
                                        '"উৎসে কর্তনকৃত মূসকের পরিমাণ" on the Mushak 6.6 VDS Certificate.')
    vat_amount = fields.Monetary(
        string='VAT Amount (Tk.)', currency_field='currency_id',
        help='Total VAT charged on the Bill Amount (before withholding) - printed as "মূসকের পরিমাণ" '
             'on the Mushak 6.6 VDS Certificate. Defaults to WHVAT (Tk.) when left blank, but edit it '
             'if only part of the VAT charged was withheld.')
    net_payment = fields.Monetary(string='Net Payment (Tk.)', currency_field='currency_id',
                                  compute='_compute_net_payment', store=True)

    payment_mode = fields.Selection(PAYMENT_MODE_SELECTION, string='Payment Mode', required=True, default='beftn')
    value_date = fields.Date(string='Value Date', default=fields.Date.context_today)
    instrument_no = fields.Char(string='Inst. No.',
                                help='Cheque number for Cheque payment modes; auto-filled with the shared '
                                     'BEFTN Reference No. once the BEFTN letter is printed.')
    purpose = fields.Char(string='Purpose')
    payment_description = fields.Char(
        string='Description of Payment', copy=True,
        help='What this payment is for. Printed on the BEFTN letter and the RTGS application.')
    section_name = fields.Char(
        string='Section Name', copy=True,
        help='Tax / VDS section applicable to this payment. Printed on the BEFTN letter and the RTGS application.')

    bank_id = fields.Many2one('res.partner.bank', string="Beneficiary's Bank Account",
                              domain="[('partner_id', '=', partner_id)]")
    beneficiary_bank_name = fields.Char(string="Beneficiary's Bank")
    beneficiary_bank_branch = fields.Char(string='Branch Name')
    beneficiary_bank_routing_no = fields.Char(string="Bank's Routing No.")
    beneficiary_account_number = fields.Char(string='Account Number')
    beneficiary_address = fields.Char(string='Beneficiary Address')

    # ---- Our debit account, chosen per line (was a request-level field) ----
    company_partner_id = fields.Many2one(related='company_id.partner_id', string='Company Contact')
    own_bank_id = fields.Many2one(
        'res.partner.bank', string='Debit Account (Our Bank)',
        domain="[('partner_id', '=', company_partner_id)]",
        default=lambda self: self.env.company.pr_own_bank_id,
        help='Our own bank account debited for this line. Pick any account of the company, or use '
             '"Create and edit" in the dropdown to add a new one.')
    own_bank_bank_id = fields.Many2one(related='own_bank_id.bank_id', string='Debit Bank')
    own_bank_branch_id = fields.Many2one(
        'payment.request.branch', string='Debit Account Branch',
        domain="['|', ('bank_id', '=', False), ('bank_id', '=', own_bank_bank_id)]",
        default=lambda self: self._default_own_bank_branch(),
        help='Branch of the debit account. Pick one or type a new name and create it from the dropdown.')

    payment_move_id = fields.Many2one('account.move', string='Payment Journal Entry', readonly=True, copy=False)
    is_paid = fields.Boolean(string='Paid', compute='_compute_is_paid', store=True)

    amount_in_words = fields.Char(string='Amount in Words', compute='_compute_amount_in_words')

    @api.model
    def _default_own_bank_branch(self):
        name = (self.env.company.pr_own_bank_branch or '').strip()
        if not name:
            return False
        return self.env['payment.request.branch'].search([('name', '=', name)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        # Lines created from code (e.g. TT -> Payment Request hand-off) never run onchanges,
        # so fill everything that comes from the Vendor Profile here when it was not given.
        for vals in vals_list:
            partner = self.env['res.partner'].browse(vals['partner_id']) if vals.get('partner_id') else False
            if partner:
                for key, value in self._vendor_profile_vals(partner, vals.get('bill_amount')).items():
                    if not vals.get(key):
                        vals[key] = value
            # Invoice Ref./Date come from the linked Vendor Bill when not given
            if vals.get('invoice_id') and not (vals.get('invoice_ref') and vals.get('invoice_date')):
                bill = self.env['account.move'].browse(vals['invoice_id'])
                if not vals.get('invoice_ref'):
                    vals['invoice_ref'] = bill.ref or bill.name
                if not vals.get('invoice_date'):
                    vals['invoice_date'] = bill.invoice_date
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('invoice_id'):
            for rec in self:
                if not rec.invoice_ref:
                    rec.invoice_ref = rec.invoice_id.ref or rec.invoice_id.name
                if not rec.invoice_date:
                    rec.invoice_date = rec.invoice_id.invoice_date
        return res

    @api.depends('invoice_id.x_vat_challan_no', 'invoice_id.x_vat_challan_date')
    def _compute_vat_challan(self):
        for rec in self:
            if rec.invoice_id:
                rec.vat_challan_no = rec.invoice_id.x_vat_challan_no
                rec.vat_challan_date = rec.invoice_id.x_vat_challan_date
            else:   # manual lines keep what was typed
                rec.vat_challan_no = rec.vat_challan_no
                rec.vat_challan_date = rec.vat_challan_date

    @api.depends('invoice_id.x_due_date_calc')
    def _compute_due_date(self):
        for rec in self:
            if rec.invoice_id:
                rec.due_date = rec.invoice_id.x_due_date_calc
            else:   # manual / expense lines keep what was typed or set when the line was created
                rec.due_date = rec.due_date

    @api.model
    def _plain_text(self, text, limit=0):
        text = re.sub(r'<[^>]+>', ' ', text or '')
        text = ' '.join(html.unescape(text).split())
        if limit and len(text) > limit:
            text = text[:limit - 1].rstrip() + '\u2026'
        return text

    @api.model
    def _purpose_from_bill(self, bill):
        """The bill's note is an HTML field and can be very long - keep a short plain-text version."""
        return self._plain_text(bill.narration, 200) or bill.ref or bill.name or ''

    def report_purpose(self, limit=160):
        """Short, plain, wrap-safe text for the printed requisition."""
        self.ensure_one()
        return self._plain_text(self.purpose or self.payment_description, limit)

    @api.depends('bill_amount', 'deduction_amount', 'wht_amount', 'whvat_amount')
    def _compute_net_payment(self):
        for rec in self:
            rec.net_payment = rec.bill_amount - rec.deduction_amount - rec.wht_amount - rec.whvat_amount

    @api.depends('payment_move_id')
    def _compute_is_paid(self):
        for rec in self:
            rec.is_paid = bool(rec.payment_move_id)

    @api.depends('net_payment')
    def _compute_amount_in_words(self):
        for rec in self:
            rec.amount_in_words = amount_to_words_bdt(rec.net_payment)

    @api.constrains('bill_amount', 'deduction_amount', 'wht_amount', 'whvat_amount')
    def _check_amounts(self):
        for rec in self:
            if rec.bill_amount <= 0:
                raise ValidationError('Bill Amount must be greater than zero.')
            if rec.deduction_amount < 0 or rec.wht_amount < 0 or rec.whvat_amount < 0:
                raise ValidationError('Deduction/WHT/WHVAT cannot be negative.')
            if rec.net_payment < 0:
                raise ValidationError(
                    'Net Payment cannot be negative for %s - check Deduction/WHT/WHVAT against Bill Amount.'
                    % (rec.partner_id.name or ''))

    @api.constrains('invoice_id', 'request_id')
    def _check_invoice_not_in_other_request(self):
        """The same Vendor Bill can sit in only ONE live Payment Request (cancelled / rejected ones
        do not count), so it can never be requested - and paid - twice."""
        for rec in self:
            if not rec.invoice_id or rec.request_id.state in ('cancelled', 'rejected'):
                continue
            other = self.search([
                ('id', '!=', rec.id), ('invoice_id', '=', rec.invoice_id.id),
                ('request_state', 'not in', ('cancelled', 'rejected'))], limit=1)
            if other:
                raise ValidationError(
                    'Vendor Bill %s is already in Payment Request %s. One bill can be paid only once.'
                    % (rec.invoice_id.name, other.request_id.name))

    @api.constrains('invoice_id', 'bill_amount')
    def _check_invoice_amount(self):
        for rec in self:
            if rec.invoice_id and rec.bill_amount - rec.invoice_id.amount_residual > 0.01:
                raise ValidationError(
                    'Bill Amount (%.2f) exceeds the outstanding balance (%.2f) of Vendor Bill %s.'
                    % (rec.bill_amount, rec.invoice_id.amount_residual, rec.invoice_id.name))

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        for rec in self:
            if rec.invoice_id:
                rec.partner_id = rec.invoice_id.partner_id
                rec.bill_amount = rec.invoice_id.amount_residual
                rec.invoice_ref = rec.invoice_id.ref or rec.invoice_id.name
                rec.invoice_date = rec.invoice_id.invoice_date
                if not rec.purpose:
                    rec.purpose = self._purpose_from_bill(rec.invoice_id)

    @api.model
    def _vendor_profile_vals(self, partner, bill_amount=0.0):
        """Everything this line takes from the Vendor Profile (custom_contacts / product_vendor_details)."""
        vals = {
            'vendor_bin': partner.x_bin_no or partner.vat or False,
            'beneficiary_address': partner.contact_address or partner.name,
            'section_name': partner.x_tds_section_ref or False,
        }
        # Beneficiary bank: the vendor's "Bank Info" tab first, Odoo bank account as fallback
        fallback = partner.bank_ids[:1]
        vals.update({
            'beneficiary_bank_name': partner.x_bank_name or fallback.bank_id.name or False,
            'beneficiary_bank_branch': partner.x_bank_branch or False,
            'beneficiary_bank_routing_no': partner.x_bank_routing_no or False,
            'beneficiary_account_number': partner.x_bank_account_no or fallback.acc_number or False,
        })
        if partner.x_vat_tds_type == 'including' and bill_amount:
            vals['wht_amount'] = round(bill_amount * (partner.x_tds_percent or 0.0) / 100.0, 2)
            vals['whvat_amount'] = round(bill_amount * (partner.x_vat_percent or 0.0) / 100.0, 2)
        return vals

    @api.onchange('partner_id', 'bill_amount')
    def _onchange_partner_id(self):
        for rec in self:
            partner = rec.partner_id
            if not partner:
                rec.bank_id = False
                continue
            vals = self._vendor_profile_vals(partner, rec.bill_amount)
            for key, value in vals.items():
                # bank / BIN / section follow the vendor; WHT / WHVAT follow the % on every bill change
                rec[key] = value
            rec.bank_id = partner.bank_ids[:1] if partner.bank_ids else False
            if vals.get('whvat_amount') and not rec.vat_amount:
                rec.vat_amount = vals['whvat_amount']

    @api.onchange('own_bank_id')
    def _onchange_own_bank_id(self):
        for rec in self:
            branch = rec.own_bank_branch_id
            if branch and branch.bank_id and branch.bank_id != rec.own_bank_id.bank_id:
                rec.own_bank_branch_id = False   # branch belongs to another bank
            if not rec.own_bank_branch_id:
                default = self._default_own_bank_branch()
                if default and (not default.bank_id or default.bank_id == rec.own_bank_id.bank_id):
                    rec.own_bank_branch_id = default

    @api.onchange('whvat_amount')
    def _onchange_whvat_amount(self):
        for rec in self:
            if rec.whvat_amount and not rec.vat_amount:
                rec.vat_amount = rec.whvat_amount

    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        for rec in self:
            if rec.bank_id:
                rec.beneficiary_bank_name = rec.bank_id.bank_id.name or rec.beneficiary_bank_name
                rec.beneficiary_account_number = rec.bank_id.acc_number or rec.beneficiary_account_number

    def unlink(self):
        for rec in self:
            if rec.request_id.state != 'draft':
                raise UserError('Cannot delete a line once its Payment Request has left Draft '
                                '(audit trail). Reset the request to Draft first if this line was '
                                'added in error.')
        return super().unlink()

    def action_create_vendor_payment(self):
        self.ensure_one()
        if self.payment_move_id:
            raise UserError('A Payment Journal Entry already exists for this line.')
        if not self.invoice_id:
            raise UserError('Link a Vendor Bill (Invoice) to this line first.')
        if self.invoice_id.state != 'posted':
            raise UserError('The linked Vendor Bill must be Posted.')
        if self.invoice_id.payment_state in ('paid', 'in_payment', 'reversed'):
            raise UserError('Vendor Bill %s is already paid in Accounting.' % self.invoice_id.name)
        company = self.company_id
        journal = company.pr_journal_id
        bank_account = company.pr_bank_account_id
        if not journal or not bank_account:
            raise UserError('Configure "Payment Request Journal" and "Bank Account" in '
                            'Settings > Payment Request first.')
        if self.wht_amount and not company.pr_tds_payable_account_id:
            raise UserError('Configure "TDS (WHT) Payable Account" in Settings > Payment Request first.')
        if self.whvat_amount and not company.pr_vds_payable_account_id:
            raise UserError('Configure "VDS (WHVAT) Payable Account" in Settings > Payment Request first.')

        payable_line = self.invoice_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
        if not payable_line:
            raise UserError('Could not find an open Accounts Payable line on Vendor Bill %s.'
                            % self.invoice_id.name)
        payable_account = payable_line[0].account_id
        settle_amount = self.bill_amount - self.deduction_amount

        lines = [(0, 0, {
            'account_id': payable_account.id,
            'partner_id': self.partner_id.id,
            'name': 'Payment Request %s - %s' % (self.request_id.name, self.invoice_id.name),
            'debit': settle_amount, 'credit': 0.0,
        })]
        if self.wht_amount:
            lines.append((0, 0, {
                'account_id': company.pr_tds_payable_account_id.id,
                'partner_id': self.partner_id.id,
                'name': 'WHT (TDS) - %s' % self.invoice_id.name,
                'debit': 0.0, 'credit': self.wht_amount,
            }))
        if self.whvat_amount:
            lines.append((0, 0, {
                'account_id': company.pr_vds_payable_account_id.id,
                'partner_id': self.partner_id.id,
                'name': 'WHVAT (VDS) - %s' % self.invoice_id.name,
                'debit': 0.0, 'credit': self.whvat_amount,
            }))
        lines.append((0, 0, {
            'account_id': bank_account.id,
            'partner_id': self.partner_id.id,
            'name': 'Payment Request %s - %s' % (self.request_id.name, self.invoice_id.name),
            'debit': 0.0, 'credit': self.net_payment,
        }))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.value_date or fields.Date.context_today(self),
            'ref': 'Payment Request %s - %s' % (self.request_id.name, self.partner_id.name),
            'line_ids': lines,
        })
        move.action_post()
        self.payment_move_id = move.id

        # Reconcile our new AP line against the bill's open AP line, up to
        # (Bill Amount - Deduction). If Deduction > 0, this deliberately
        # leaves that much still open on the bill for you to reconcile
        # manually against the relevant advance payment.
        new_payable_line = move.line_ids.filtered(lambda l: l.account_id == payable_account and l.debit)
        (payable_line + new_payable_line).reconcile()
        return True