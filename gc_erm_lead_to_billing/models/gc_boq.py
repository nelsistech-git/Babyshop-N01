# -*- coding: utf-8 -*-
"""Bill of Quantities, costing formula and costing controls (SRS 17 - 19)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .gc_service_catalog import MARGIN_METHOD_SELECTION

BOQ_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('locked', 'Locked'),
    ('revised', 'Superseded'),
    ('cancelled', 'Cancelled'),
]


class GcErmBoq(models.Model):
    _name = 'gc.erm.boq'
    _description = 'GC ERM Bill of Quantities'
    _inherit = ['gc.erm.document.mixin']
    _order = 'survey_id, version desc, id desc'

    _gc_sequence_code = 'gc.erm.boq'
    _gc_closed_states = ('locked', 'revised', 'cancelled')

    state = fields.Selection(
        BOQ_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True)

    # ------------------------------------------------------------------
    # Header (SRS 17)
    # ------------------------------------------------------------------
    survey_id = fields.Many2one(
        'gc.erm.survey', string='Survey', required=True, ondelete='restrict',
        index=True, tracking=True)
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', related='survey_id.lead_id', store=True,
        index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True,
        tracking=True)
    prepared_by_id = fields.Many2one(
        'res.users', string='Prepared By', default=lambda self: self.env.user,
        required=True, tracking=True)
    prepared_date = fields.Date(
        string='Prepared Date', default=fields.Date.context_today, required=True)
    version = fields.Integer(string='Version', default=1, readonly=True, copy=False)
    revision_of_id = fields.Many2one(
        'gc.erm.boq', string='Revision Of', readonly=True, copy=False,
        ondelete='set null', index=True)
    revision_ids = fields.One2many(
        'gc.erm.boq', 'revision_of_id', string='Revisions')
    revision_count = fields.Integer(compute='_compute_revision_count')

    technical_report_ids = fields.One2many(
        'gc.erm.technical.report', 'boq_id', string='Technical Reports')

    # ------------------------------------------------------------------
    # Costing configuration (SRS 18)
    # ------------------------------------------------------------------
    margin_method = fields.Selection(
        MARGIN_METHOD_SELECTION, string='Margin Method', required=True,
        default=lambda self: self._default_margin_method(), tracking=True,
        help='Fixed amount, percentage on cost or percentage on selling price.')
    margin_value = fields.Float(
        string='Margin Value', default=lambda self: self._default_margin_value(),
        tracking=True,
        help='Applied to every line that does not override it.')
    global_discount = fields.Float(
        string='Global Discount (%)', default=0.0,
        help='Applied on top of the per-line discounts.')

    line_ids = fields.One2many(
        'gc.erm.boq.line', 'boq_id', string='BOQ Lines', copy=True)
    line_count = fields.Integer(compute='_compute_amounts', store=True)

    # ------------------------------------------------------------------
    # Totals (SRS 18)
    # ------------------------------------------------------------------
    total_material_cost = fields.Monetary(
        string='Material Cost', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    total_installation_cost = fields.Monetary(
        string='Installation Cost', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    total_transport_cost = fields.Monetary(
        string='Transport Cost', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    total_other_cost = fields.Monetary(
        string='Other Cost', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    total_cost = fields.Monetary(
        string='Total Internal Cost', compute='_compute_amounts', store=True,
        currency_field='currency_id',
        help='Sum of the internal cost of every line (SRS 18).')
    total_margin = fields.Monetary(
        string='Total Margin', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    total_discount = fields.Monetary(
        string='Total Discount', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_untaxed = fields.Monetary(
        string='Selling Price (untaxed)', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_tax = fields.Monetary(
        string='Taxes', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_total = fields.Monetary(
        string='Total Selling Price', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    margin_percentage = fields.Float(
        string='Margin (%)', compute='_compute_amounts', store=True,
        digits=(16, 2))

    note = fields.Html(string='Costing Notes', sanitize=True)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _default_margin_method(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'gc_erm.default_margin_method', 'cost_pct')

    @api.model
    def _default_margin_value(self):
        try:
            return float(self.env['ir.config_parameter'].sudo().get_param(
                'gc_erm.default_margin_value', '20') or 0)
        except (TypeError, ValueError):
            return 20.0

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('line_ids.material_cost', 'line_ids.installation_cost',
                 'line_ids.transport_cost', 'line_ids.other_cost',
                 'line_ids.line_cost', 'line_ids.margin_amount',
                 'line_ids.discount_amount', 'line_ids.price_subtotal',
                 'line_ids.price_tax', 'line_ids.price_total',
                 'global_discount', 'currency_id')
    def _compute_amounts(self):
        for boq in self:
            lines = boq.line_ids
            boq.line_count = len(lines)
            boq.total_material_cost = sum(lines.mapped('material_cost'))
            boq.total_installation_cost = sum(lines.mapped('installation_cost'))
            boq.total_transport_cost = sum(lines.mapped('transport_cost'))
            boq.total_other_cost = sum(lines.mapped('other_cost'))
            boq.total_cost = sum(lines.mapped('line_cost'))
            boq.total_margin = sum(lines.mapped('margin_amount'))
            line_discount = sum(lines.mapped('discount_amount'))
            untaxed = sum(lines.mapped('price_subtotal'))
            global_disc_amount = untaxed * (boq.global_discount or 0.0) / 100.0
            untaxed -= global_disc_amount
            taxes = sum(lines.mapped('price_tax'))
            if boq.global_discount:
                # Taxes follow the discounted base proportionally.
                base = sum(lines.mapped('price_subtotal')) or 1.0
                taxes = taxes * (untaxed / base)
            boq.total_discount = line_discount + global_disc_amount
            boq.amount_untaxed = untaxed
            boq.amount_tax = taxes
            boq.amount_total = untaxed + taxes
            boq.margin_percentage = (
                (untaxed - boq.total_cost) / untaxed * 100.0) if untaxed else 0.0

    @api.depends('revision_ids')
    def _compute_revision_count(self):
        for boq in self:
            boq.revision_count = len(boq.revision_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('margin_method', 'margin_value')
    def _check_margin(self):
        for boq in self:
            if boq.margin_value < 0:
                raise ValidationError(_('The margin value cannot be negative.'))
            if boq.margin_method == 'price_pct' and boq.margin_value >= 100:
                raise ValidationError(_(
                    'A margin expressed as a percentage on selling price must '
                    'be strictly below 100%.'))

    @api.constrains('global_discount')
    def _check_global_discount(self):
        for boq in self:
            if not 0.0 <= boq.global_discount <= 100.0:
                raise ValidationError(_(
                    'The global discount must be between 0 and 100 percent.'))

    # ------------------------------------------------------------------
    # Costing controls (SRS 19)
    # ------------------------------------------------------------------
    def _is_locked(self):
        self.ensure_one()
        return self.state in ('locked', 'revised', 'cancelled')

    EDITABLE_WHEN_LOCKED = ('state', 'message_follower_ids', 'message_ids',
                            'activity_ids', 'revision_of_id', 'color',
                            'sla_deadline', 'sla_state')

    def write(self, vals):
        if not self.env.context.get('gc_bypass_lock'):
            touched = set(vals) - set(self.EDITABLE_WHEN_LOCKED)
            if touched:
                for boq in self:
                    if boq._is_locked():
                        raise UserError(_(
                            "BOQ %(name)s (version %(version)s) is locked "
                            "because the technical report was submitted. "
                            "Create a controlled revision instead of editing "
                            "the approved costing.",
                            name=boq.name, version=boq.version))
                    if boq.state == 'confirmed' and self.env.user.has_group(
                            'gc_erm_lead_to_billing.group_gc_sales_user') \
                            and not self.env.user.has_group(
                                'gc_erm_lead_to_billing.group_gc_technical_user'):
                        raise UserError(_(
                            'Sales users cannot change a confirmed technical '
                            'costing (BOQ %s).', boq.name))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        for boq in self:
            if boq.state != 'draft':
                raise UserError(_('Only a draft BOQ can be confirmed.'))
            if not boq.line_ids:
                raise UserError(_(
                    'BOQ %s has no lines. Add at least one product or service.',
                    boq.name))
            boq._gc_transition(
                'confirmed', comment=_('BOQ confirmed by %s',
                                       self.env.user.name),
                allowed_from=('draft',))
        return True

    def action_lock(self):
        """Called when the technical report is submitted (SRS 19)."""
        for boq in self:
            if boq.state not in ('draft', 'confirmed'):
                continue
            boq.with_context(gc_bypass_lock=True)._gc_transition(
                'locked',
                comment=_('BOQ locked - technical report submitted.'))
        return True

    def action_create_revision(self):
        """Controlled revision keeping the previous version auditable."""
        self.ensure_one()
        if self.state not in ('confirmed', 'locked'):
            raise UserError(_(
                'Only a confirmed or locked BOQ can be revised.'))
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_technical_user',
            _('revise a bill of quantities'))
        new_boq = self.with_context(gc_bypass_lock=True).copy({
            'version': self.version + 1,
            'revision_of_id': self.id,
            'state': 'draft',
            'prepared_by_id': self.env.user.id,
            'prepared_date': fields.Date.context_today(self),
        })
        self.with_context(gc_bypass_lock=True)._gc_transition(
            'revised', comment=_('Superseded by revision %s (v%s).',
                                 new_boq.name, new_boq.version))
        new_boq.message_post(body=_(
            'Revision %(v)s created from %(src)s.',
            v=new_boq.version, src=self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('BOQ Revision'),
            'res_model': 'gc.erm.boq',
            'res_id': new_boq.id,
            'view_mode': 'form',
        }

    def action_reset_draft(self):
        for boq in self:
            if boq.state != 'confirmed':
                raise UserError(_(
                    'Only a confirmed BOQ can be reset to draft. A locked BOQ '
                    'must go through the revision process.'))
            boq.with_context(gc_bypass_lock=True)._gc_transition(
                'draft', comment=_('Reset to draft.'), allowed_from=('confirmed',))
        return True

    def action_cancel(self):
        for boq in self:
            if boq.technical_report_ids.filtered(
                    lambda r: r.state not in ('draft', 'cancelled')):
                raise UserError(_(
                    'BOQ %s is used by a submitted technical report and cannot '
                    'be cancelled.', boq.name))
            boq.with_context(gc_bypass_lock=True)._gc_transition(
                'cancelled', comment=_('BOQ cancelled.'))
        return True

    def action_view_revisions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('BOQ Revisions'),
            'res_model': 'gc.erm.boq',
            'view_mode': 'tree,form',
            'domain': ['|', ('revision_of_id', '=', self.id), ('id', '=', self.id)],
        }

    def action_recompute_prices(self):
        """Re-apply the header margin method to every line."""
        for boq in self:
            if boq._is_locked():
                raise UserError(_('BOQ %s is locked.', boq.name))
            for line in boq.line_ids:
                line.use_header_margin = True
            boq.line_ids._compute_margin_method()
            boq.line_ids._compute_margin_value()
            boq.line_ids._compute_costing()
            boq.line_ids._compute_sales_price()
        return True

    @api.depends('name', 'version', 'partner_id')
    def _compute_display_name(self):
        for boq in self:
            boq.display_name = '%s v%s' % (boq.name, boq.version)


class GcErmBoqLine(models.Model):
    _name = 'gc.erm.boq.line'
    _description = 'GC ERM BOQ Line'
    _order = 'boq_id, sequence, id'

    boq_id = fields.Many2one(
        'gc.erm.boq', string='BOQ', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='boq_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='boq_id.currency_id', store=True)
    partner_id = fields.Many2one(related='boq_id.partner_id')
    state = fields.Selection(related='boq_id.state', string='BOQ Status')

    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain="[('sale_ok', '=', True)]")
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(
        string='Quantity', default=1.0, required=True,
        digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM')

    # ---- Cost side (SRS 17 / 18) --------------------------------------
    unit_cost = fields.Monetary(
        string='Unit Cost', currency_field='currency_id')
    material_cost = fields.Monetary(
        string='Material Cost', compute='_compute_costing', store=True,
        currency_field='currency_id',
        help='Quantity x Unit Cost.')
    installation_cost = fields.Monetary(
        string='Installation Cost', currency_field='currency_id')
    transport_cost = fields.Monetary(
        string='Transport Cost', currency_field='currency_id')
    other_cost = fields.Monetary(
        string='Other Cost', currency_field='currency_id')
    line_cost = fields.Monetary(
        string='Line Internal Cost', compute='_compute_costing', store=True,
        currency_field='currency_id',
        help='Material + Installation + Transport + Other.')

    # ---- Selling side --------------------------------------------------
    use_header_margin = fields.Boolean(
        string='Use Header Margin', default=True,
        help='Uncheck to define a specific margin for this line.')
    margin_method = fields.Selection(
        MARGIN_METHOD_SELECTION, string='Margin Method',
        compute='_compute_margin_method', store=True, readonly=False)
    margin_value = fields.Float(
        string='Margin Value', compute='_compute_margin_value', store=True,
        readonly=False)
    margin_amount = fields.Monetary(
        string='Margin Amount', compute='_compute_costing', store=True,
        currency_field='currency_id')
    sales_price = fields.Float(
        string='Unit Sales Price', compute='_compute_sales_price', store=True,
        readonly=False, digits=(16, 6),
        help='Computed from the internal cost and the margin. Kept at six '
             'decimals so that "cost + margin" ties out exactly on large '
             'quantities; the customer facing documents round it to the '
             'currency precision. It can be overridden manually, and changing '
             'any cost or margin input recomputes it again.')
    price_gross = fields.Monetary(
        string='Gross Amount', compute='_compute_totals', store=True,
        currency_field='currency_id')
    discount = fields.Float(string='Discount (%)', default=0.0)
    discount_amount = fields.Monetary(
        string='Discount Amount', compute='_compute_totals', store=True,
        currency_field='currency_id')
    tax_ids = fields.Many2many(
        'account.tax', 'gc_boq_line_tax_rel', 'line_id', 'tax_id',
        string='Taxes', domain="[('type_tax_use', '=', 'sale')]")
    price_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_totals', store=True,
        currency_field='currency_id')
    price_tax = fields.Monetary(
        string='Tax Amount', compute='_compute_totals', store=True,
        currency_field='currency_id')
    price_total = fields.Monetary(
        string='Total', compute='_compute_totals', store=True,
        currency_field='currency_id')
    line_margin_pct = fields.Float(
        string='Margin (%)', compute='_compute_totals', store=True,
        digits=(16, 2))
    remarks = fields.Char(string='Remarks')

    # ------------------------------------------------------------------
    # Costing controls (SRS 19) -- the lock must cover the lines too,
    # otherwise an approved costing could be changed line by line.
    # ------------------------------------------------------------------
    def _check_boq_editable(self):
        if self.env.context.get('gc_bypass_lock'):
            return True
        for line in self:
            boq = line.boq_id
            if boq and boq._is_locked():
                raise UserError(_(
                    "BOQ %(name)s (version %(version)s) is locked. Create a "
                    "controlled revision instead of editing its lines.",
                    name=boq.name, version=boq.version))
            if boq and boq.state == 'confirmed' and \
                    self.env.user.has_group(
                        'gc_erm_lead_to_billing.group_gc_sales_user') and \
                    not self.env.user.has_group(
                        'gc_erm_lead_to_billing.group_gc_technical_user'):
                raise UserError(_(
                    'Sales users cannot change a confirmed technical costing '
                    '(BOQ %s).', boq.name))
        return True

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_boq_editable()
        return lines

    def write(self, vals):
        self._check_boq_editable()
        return super().write(vals)

    def unlink(self):
        self._check_boq_editable()
        return super().unlink()

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    # NOTE: ``margin_method``, ``margin_value`` and ``sales_price`` are
    # editable computed fields.  Each one therefore gets its OWN compute
    # method: Odoo skips a whole compute method when any of the fields it
    # produces is supplied in the create values (which happens on copy), so
    # grouping a read-only field with an editable one would silently leave the
    # read-only field at zero.
    @api.depends('use_header_margin', 'boq_id.margin_method')
    def _compute_margin_method(self):
        for line in self:
            if line.use_header_margin:
                line.margin_method = line.boq_id.margin_method or 'cost_pct'
            else:
                line.margin_method = line.margin_method or \
                    line.boq_id.margin_method or 'cost_pct'

    @api.depends('use_header_margin', 'boq_id.margin_value')
    def _compute_margin_value(self):
        for line in self:
            if line.use_header_margin:
                line.margin_value = line.boq_id.margin_value or 0.0
            else:
                line.margin_value = line.margin_value or 0.0

    @api.depends('quantity', 'unit_cost', 'installation_cost', 'transport_cost',
                 'other_cost', 'margin_method', 'margin_value')
    def _compute_costing(self):
        """SRS 18 -- the costing formula (read-only outputs only)."""
        for line in self:
            material = line.quantity * line.unit_cost
            line.material_cost = material
            cost = (material + line.installation_cost + line.transport_cost
                    + line.other_cost)
            line.line_cost = cost
            line.margin_amount = line._compute_margin_amount(cost)

    @api.depends('line_cost', 'margin_amount', 'quantity')
    def _compute_sales_price(self):
        """Unit selling price derived from the cost and the margin."""
        for line in self:
            gross = line.line_cost + line.margin_amount
            line.sales_price = (gross / line.quantity) if line.quantity else gross

    def _compute_margin_amount(self, cost):
        """Return the margin amount for ``cost`` using the line's method."""
        self.ensure_one()
        value = self.margin_value or 0.0
        method = self.margin_method or 'cost_pct'
        if method == 'fixed':
            return value
        if method == 'cost_pct':
            return cost * value / 100.0
        if method == 'price_pct':
            # margin / (cost + margin) = value%  =>  margin = cost*v/(100-v)
            if value >= 100.0:
                return 0.0
            return cost * value / (100.0 - value)
        return 0.0

    @api.depends('sales_price', 'quantity', 'discount', 'tax_ids',
                 'line_cost', 'partner_id', 'currency_id')
    def _compute_totals(self):
        for line in self:
            gross = line.sales_price * line.quantity
            line.price_gross = gross
            discount_amount = gross * (line.discount or 0.0) / 100.0
            line.discount_amount = discount_amount
            net = gross - discount_amount
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    line.sales_price * (1 - (line.discount or 0.0) / 100.0),
                    currency=line.currency_id or line.company_id.currency_id,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=line.partner_id)
                line.price_subtotal = taxes['total_excluded']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
                line.price_total = taxes['total_included']
            else:
                line.price_subtotal = net
                line.price_tax = 0.0
                line.price_total = net
            line.line_margin_pct = (
                (line.price_subtotal - line.line_cost) / line.price_subtotal * 100.0
            ) if not float_is_zero(
                line.price_subtotal, precision_rounding=0.01) else 0.0

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            line.name = product.get_product_multiline_description_sale() \
                if hasattr(product, 'get_product_multiline_description_sale') \
                else (product.display_name or '')
            line.uom_id = product.uom_id
            line.unit_cost = product.standard_price
            fiscal_taxes = product.taxes_id.filtered(
                lambda t: t.company_id == (line.company_id or self.env.company))
            line.tax_ids = [(6, 0, fiscal_taxes.ids)]

    @api.onchange('use_header_margin')
    def _onchange_use_header_margin(self):
        for line in self:
            if line.use_header_margin and line.boq_id:
                line.margin_method = line.boq_id.margin_method
                line.margin_value = line.boq_id.margin_value

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if float_compare(line.quantity, 0.0, precision_digits=4) <= 0:
                raise ValidationError(_(
                    'The quantity of line "%s" must be greater than zero.',
                    line.name or line.product_id.display_name))

    @api.constrains('discount')
    def _check_discount(self):
        for line in self:
            if not 0.0 <= line.discount <= 100.0:
                raise ValidationError(_(
                    'The discount of line "%s" must be between 0 and 100 percent.',
                    line.name or ''))

    @api.constrains('unit_cost', 'installation_cost', 'transport_cost',
                    'other_cost')
    def _check_costs(self):
        for line in self:
            if min(line.unit_cost, line.installation_cost,
                   line.transport_cost, line.other_cost) < 0:
                raise ValidationError(_(
                    'Costs of line "%s" cannot be negative.',
                    line.name or ''))
