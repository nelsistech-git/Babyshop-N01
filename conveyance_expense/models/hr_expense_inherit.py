from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Fields the "My Expenses" form no longer shows: their values come from the Expense Details lines
# (Category and Date columns) and the Total is the sum of the lines.
FORM_HIDDEN_FIELDS = ('product_id', 'date', 'total_amount_currency', 'total_amount', 'product_uom_id', 'quantity')


class HrExpenseInherit(models.Model):
    _inherit = 'hr.expense'

    conveyance_sheet_ids = fields.One2many(
        comodel_name='conveyance.sheet',
        inverse_name='expense_id',
        string='Conveyance Sheets',
    )
    employee_designation_id = fields.Many2one(
        comodel_name='hr.job',
        string='Designation',
        related='employee_id.job_id',
        readonly=True,
    )
    conveyance_sheet_count = fields.Integer(
        string='Conveyance Count',
        compute='_compute_conveyance_sheet_count',
    )
    # The (first) sheet linked to this expense; its lines are edited inline
    conveyance_sheet_id = fields.Many2one(
        comodel_name='conveyance.sheet',
        string='Conveyance Sheet',
        compute='_compute_conveyance_sheet_id',
        store=True,    # stored => searchable, which Odoo needs to refresh conveyance_line_ids correctly
    )
    conveyance_line_ids = fields.One2many(
        related='conveyance_sheet_id.line_ids',
        string='Conveyance Lines',
        readonly=False,
    )

    @api.depends('conveyance_sheet_ids')
    def _compute_conveyance_sheet_id(self):
        for rec in self:
            rec.conveyance_sheet_id = rec.conveyance_sheet_ids[:1]

    def _compute_conveyance_sheet_count(self):
        for rec in self:
            rec.conveyance_sheet_count = len(rec.conveyance_sheet_ids)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """My Expenses form: only "What is this expense for?", Employee and Paid By stay on top
        (plus the Expense Details lines). Category, Expense Date and Total are hidden - they are
        columns of the lines. Done here, by field name, so it does not depend on the exact layout
        of the standard form; the line list (inside <tree>) is never touched."""
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for name in FORM_HIDDEN_FIELDS:
                for node in arch.xpath("//field[@name='%s'][not(ancestor::tree)][not(ancestor::kanban)]" % name):
                    node.set('invisible', '1')
                    node.set('required', '0')
                for node in arch.xpath("//label[@for='%s']" % name):
                    node.set('invisible', '1')
        return arch, view

    def _sync_product_date_from_lines(self):
        """Category and Expense Date are not on the form any more: take them from the lines
        (Category of the first line that has one, Date of the earliest line)."""
        for expense in self:
            lines = expense.conveyance_sheet_id.line_ids.sorted('date')
            if not lines:
                continue
            vals = {}
            category = next((l.category_id for l in lines if l.category_id), False)
            if category and expense.product_id != category:
                vals['product_id'] = category.id
                vals['product_uom_id'] = category.uom_id.id
            elif not expense.product_uom_id and expense.product_id.uom_id:
                vals['product_uom_id'] = expense.product_id.uom_id.id
            if lines[0].date and expense.date != lines[0].date:
                vals['date'] = lines[0].date
            if vals:
                super(HrExpenseInherit, expense).write(vals)

    def _sync_total_from_conveyance(self):
        """Keep the expense Total equal to the conveyance sheet total."""
        for expense in self:
            sheet = expense.conveyance_sheet_id
            if sheet and sheet.line_ids and expense.total_amount != sheet.total_amount:
                super(HrExpenseInherit, expense).write({'total_amount': sheet.total_amount})

    @api.onchange('conveyance_line_ids')
    def _onchange_conveyance_line_ids(self):
        for rec in self:
            lines = rec.conveyance_line_ids
            if lines:
                rec.total_amount = sum(lines.mapped('total_amount'))

    def _create_conveyance_sheet(self, line_commands):
        """Create a conveyance sheet for this expense holding the given line commands."""
        self.ensure_one()
        return self.env['conveyance.sheet'].create({
            'employee_id': self.employee_id.id,
            'expense_id': self.id,
            'line_ids': line_commands,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Category / Date are hidden on the form: derive them from the line commands
            commands = [c for c in (vals.get('conveyance_line_ids') or [])
                        if isinstance(c, (list, tuple)) and c[0] == 0 and isinstance(c[2], dict)]
            category = next((c[2]['category_id'] for c in commands if c[2].get('category_id')), False)
            if category and not vals.get('product_id'):
                vals['product_id'] = category
            # Unit of Measure is hidden on the form: take it from the category product
            if vals.get('product_id') and not vals.get('product_uom_id'):
                vals.pop('product_uom_id', None)
                product = self.env['product.product'].browse(vals['product_id'])
                if product.uom_id:
                    vals['product_uom_id'] = product.uom_id.id
            dates = [c[2]['date'] for c in commands if c[2].get('date')]
            if dates and not vals.get('date'):
                vals['date'] = min(dates)
            # "What is this expense for?" is hidden on the form: fill the name automatically
            # (the web client sends name=False for the hidden field, so Odoo does not compute it
            # from the Category - always fill it here, whether or not a Category is set)
            if not (vals.get('name') or '').strip():
                purpose = next((c[2]['purpose'] for c in commands if c[2].get('purpose')), False)
                vals['name'] = purpose or _('Conveyance Expense')
        pending_lines = [vals.pop('conveyance_line_ids', False) for vals in vals_list]
        expenses = super().create(vals_list)
        for expense, lines in zip(expenses, pending_lines):
            if lines:
                expense._create_conveyance_sheet(lines)
                expense._sync_product_date_from_lines()
                expense._sync_total_from_conveyance()
        return expenses

    def write(self, vals):
        if 'name' in vals and not (vals['name'] or '').strip():
            vals = dict(vals, name=_('Conveyance Expense'))
        lines = None
        if 'conveyance_line_ids' in vals and any(not e.conveyance_sheet_id for e in self):
            lines = vals.pop('conveyance_line_ids')
        res = super().write(vals)
        if lines:
            for expense in self.filtered(lambda e: not e.conveyance_sheet_id):
                expense._create_conveyance_sheet(lines)
        if 'conveyance_line_ids' in vals or lines:
            self._sync_product_date_from_lines()
            self._sync_total_from_conveyance()      # last: changing Category can reset the price
        if 'employee_id' in vals:
            for expense in self:
                sheet = expense.conveyance_sheet_id
                if sheet and sheet.state == 'draft':
                    sheet.write({
                        'employee_id': expense.employee_id.id,
                        'designation': expense.employee_id.job_id.id,
                    })
        return res

    def _expense_debit_splits(self):
        """[{'account', 'amount', 'product', 'name'}] - the Debit side of this expense: one entry per
        Expense Category, always on the Expense Account set on that Category (product). Detail
        (conveyance) lines are split by their own Category; a plain expense uses its Category."""
        self.ensure_one()
        company = self.company_id

        def account_of(product):
            # ONLY the Expense Account typed on the Expense Category itself (product form > Accounting).
            # No fallback to the product category / default / "Expense Clearing Account".
            account = (product.product_tmpl_id.with_company(company).property_account_expense_id
                       if product else False)
            if not account:
                raise UserError(_('The Expense Category "%s" has no Expense Account. Please set it on the '
                                  'Category (Expenses > Configuration > Expense Categories > Accounting) '
                                  'first.') % (product.display_name if product else self.name))
            return account

        employee = self.employee_id.name
        sheet_lines = self.conveyance_sheet_id.line_ids.filtered('total_amount') if self.conveyance_sheet_id else []
        groups = {}
        for line in sheet_lines:
            product = line.category_id or self.product_id
            account = account_of(product)
            key = (account.id, product.id)
            group = groups.setdefault(key, {'account': account, 'amount': 0.0, 'product': product,
                                            'name': '%s: %s' % (employee, product.display_name or self.name)})
            group['amount'] += line.total_amount
        if not groups:
            account = account_of(self.product_id)
            return [{'account': account, 'amount': self.total_amount, 'product': self.product_id,
                     'name': '%s: %s' % (employee, (self.name or '').split('\n')[0][:64])}]
        splits = list(groups.values())
        diff = self.company_currency_id.round(self.total_amount - sum(g['amount'] for g in splits))
        if diff:
            splits[0]['amount'] += diff        # rounding - the entry always equals the expense total
        return splits

    def action_open_conveyance_sheet(self):
        self.ensure_one()
        # If a sheet already exists, open it; otherwise open blank form
        existing = self.conveyance_sheet_ids[:1]
        ctx = {
            'default_employee_id': self.employee_id.id,
            'default_expense_id': self.id,
        }
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Conveyance Sheet',
            'res_model': 'conveyance.sheet',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
        if existing:
            action['res_id'] = existing.id
        return action
