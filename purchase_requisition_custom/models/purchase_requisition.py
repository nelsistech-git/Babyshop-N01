
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseRequisitionCustom(models.Model):
    _name = 'purchase.requisition.custom'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='PR Number',
        readonly=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'purchase.requisition.custom'
        ) or 'New',
        tracking=True,
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        tracking=True,
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True,
    )
    designation = fields.Char(
        string='Designation',
        compute='_compute_designation',
        store=True,
        readonly=False,
    )

    # ─── Department (hidden, backup) ─────────────────────────────────────
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        tracking=True,
    )
    line_ids = fields.One2many(
        'purchase.requisition.line',
        'requisition_id',
        string='Requisition Lines',
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        digits='Product Price',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection([
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Manager Approved'),
        ('done',      'Done'),
        ('rejected',  'Rejected'),
    ], string='Status', default='draft', tracking=True, copy=False)

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        readonly=True,
        copy=False,
    )
    purchase_order_count = fields.Integer(
        string='PO Count',
        compute='_compute_purchase_order_count',
    )
    notes = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)

    # ─────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────

    @api.depends('requester_id')
    def _compute_designation(self):
        for rec in self:
            designation = ''
            if rec.requester_id:
                # HR Employee থেকে job position আনা
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', rec.requester_id.id)
                ], limit=1)
                if employee and employee.job_id:
                    designation = employee.job_id.name
                elif employee and employee.job_title:
                    designation = employee.job_title
            rec.designation = designation

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = 1 if rec.purchase_order_id else 0

    # ─────────────────────────────────────────────────────────────────────
    # ONCHANGE
    # ─────────────────────────────────────────────────────────────────────

    @api.onchange('requester_id')
    def _onchange_requester_id(self):
        if self.requester_id:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', self.requester_id.id)
            ], limit=1)
            if employee and employee.job_id:
                self.designation = employee.job_id.name
            elif employee and employee.job_title:
                self.designation = employee.job_title
            elif self.requester_id.function:
                self.designation = self.requester_id.function
            else:
                self.designation = ''

    # ─────────────────────────────────────────────────────────────────────
    # WORKFLOW ACTIONS
    # ─────────────────────────────────────────────────────────────────────

    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please add at least one product line before submitting.'))
        self.state = 'submitted'
        self.message_post(body=_('Purchase Requisition submitted for Manager approval.'))

    def action_manager_approve(self):
        self.ensure_one()
        self.state = 'approved'
        self.message_post(body=_('Approved by Manager.'))

    def action_done(self):
        self.ensure_one()
        self.state = 'done'
        self.message_post(body=_('Purchase Requisition completed.'))

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'
        self.message_post(body=_('Purchase Requisition has been rejected.'))

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'
        self.rejection_reason = False
        self.message_post(body=_('Purchase Requisition reset to Draft.'))

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError(_('No Purchase Order linked to this requisition.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_report(self):
        return self.env.ref(
            'purchase_requisition_custom.action_purchase_requisition_report'
        ).report_action(self)