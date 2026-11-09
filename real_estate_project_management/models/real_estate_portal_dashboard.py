# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

STAFF_GROUP = 'real_estate_project_management.group_real_estate_user'
CUSTOMER_GROUP = 'real_estate_project_management.group_real_estate_customer_portal'
AGENT_GROUP = 'real_estate_project_management.group_real_estate_agent'

INSTALLMENT_LABELS = {
    'paid': 'Paid', 'overdue': 'Overdue', 'partially_paid': 'Partially Paid',
    'due_today': 'Due Today', 'upcoming': 'Upcoming', 'cancelled': 'Cancelled',
}
PAYMENT_STATUS_LABELS = {
    'completed': 'Fully Paid', 'overdue': 'Overdue', 'in_progress': 'On Track',
    'not_started': 'Not Started',
}
COMMISSION_LABELS = {
    'draft': 'Pending Approval', 'approved': 'Approved', 'paid': 'Paid', 'cancelled': 'Cancelled',
}
LEVEL_LABELS = {'1': 'Level 1 (Direct)', '2': 'Level 2 (Upline)'}
STAGE_LABELS = {
    'new': 'New', 'contacted': 'Contacted', 'site_visit': 'Site Visit',
    'negotiation': 'Negotiation', 'won': 'Won', 'lost': 'Lost',
}


class RealEstatePortalDashboard(models.TransientModel):
    """'My Dashboard' for the Customer and Agent roles.

    A fresh record is created each time the menu is opened (server action ->
    action_open_dashboard) and filled in with sudo(), strictly filtered by
    the logged-in user's own partner. The user therefore only ever reads
    this transient snapshot - never the underlying company records."""
    _name = 'real.estate.portal.dashboard'
    _description = 'Customer / Agent Dashboard'
    _transient_max_hours = 12.0

    role = fields.Selection([('customer', 'Customer'), ('agent', 'Agent')], required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    generated_on = fields.Datetime(default=fields.Datetime.now)

    # ---- customer + agent shared money KPIs ---------------------------
    total_value = fields.Monetary(string='Total Value')
    total_paid = fields.Monetary(string='Total Paid')
    total_due = fields.Monetary(string='Balance Due')
    overdue_amount = fields.Monetary(string='Overdue')
    payment_progress = fields.Float(string='Paid %', digits=(5, 1))
    next_due_date = fields.Date(string='Next Due Date')
    next_due_amount = fields.Monetary(string='Next Due Amount')

    # ---- customer KPIs ------------------------------------------------
    properties_count = fields.Integer()
    projects_count = fields.Integer()
    installments_paid = fields.Integer()
    installments_pending = fields.Integer()
    installments_overdue = fields.Integer()
    exp_budget = fields.Monetary(string='Project Budget')
    exp_committed = fields.Monetary(string='Committed')
    exp_actual = fields.Monetary(string='Actual Expense')
    exp_remaining = fields.Monetary(string='Remaining Budget')
    exp_utilization = fields.Float(string='Budget Used %', digits=(5, 1))

    # ---- commission KPIs (customer-as-referrer and agent) --------------
    commission_count = fields.Integer()
    commission_total = fields.Monetary(string='Total Commission')
    commission_paid = fields.Monetary(string='Commission Paid')
    commission_pending = fields.Monetary(string='Commission Pending')
    commission_l1_total = fields.Monetary(string='Level 1 Commission')
    commission_l2_total = fields.Monetary(string='Level 2 Commission')

    # ---- agent KPIs ---------------------------------------------------
    customers_count = fields.Integer()
    sales_count = fields.Integer()
    open_leads = fields.Integer()
    followups_due = fields.Integer()
    won_leads = fields.Integer()
    pipeline_value = fields.Monetary(string='Pipeline Value')

    # ---- display rows -------------------------------------------------
    line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id')
    property_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                         domain=[('line_type', '=', 'property')])
    schedule_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                         domain=[('line_type', '=', 'schedule')])
    payment_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                        domain=[('line_type', '=', 'payment')])
    project_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                        domain=[('line_type', '=', 'project')])
    expense_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                        domain=[('line_type', '=', 'expense')])
    commission_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                           domain=[('line_type', '=', 'commission')])
    customer_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                         domain=[('line_type', '=', 'customer')])
    sale_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                     domain=[('line_type', '=', 'sale')])
    followup_line_ids = fields.One2many('real.estate.portal.line', 'dashboard_id',
                                         domain=[('line_type', '=', 'followup')])

    # ==================================================================
    # Entry points
    # ==================================================================
    @api.model
    def action_open_dashboard(self, role, partner=None):
        """Menu / button entry point. Normal users always get THEIR OWN
        data; only real-estate staff may preview another partner."""
        user = self.env.user
        staff = user.has_group(STAFF_GROUP)
        if isinstance(partner, int):
            partner = self.env['res.partner'].browse(partner)
        if partner and not staff:
            raise AccessError(_('You are not allowed to open another person\'s dashboard.'))
        if role not in ('customer', 'agent'):
            raise UserError(_('Unknown dashboard role.'))
        if not staff:
            group = CUSTOMER_GROUP if role == 'customer' else AGENT_GROUP
            if not user.has_group(group):
                raise AccessError(_('You do not have access to this dashboard.'))
        partner = partner or user.partner_id
        dash = self.create({
            'role': role,
            'partner_id': partner.id,
            'partner_name': partner.name,
        })
        dash._build()
        view_xmlid = ('real_estate_project_management.view_real_estate_portal_dashboard_%s_form' % role)
        view = self.env.ref(view_xmlid)
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Dashboard') if role == 'customer' else _('Agent Dashboard'),
            'res_model': self._name,
            'res_id': dash.id,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'target': 'current',
        }

    def action_refresh(self):
        for rec in self:
            rec._build()
        return True

    def _build(self):
        self.ensure_one()
        self.sudo().line_ids.unlink()
        if self.role == 'customer':
            self._build_customer()
        else:
            self._build_agent()
        self.sudo().generated_on = fields.Datetime.now()

    # ==================================================================
    # Helpers
    # ==================================================================
    @api.model
    def _selection_label(self, record, field_name):
        field = record._fields[field_name]
        return dict(field._description_selection(self.env)).get(record[field_name], record[field_name] or '')

    @api.model
    def _installment_state(self, inst, today):
        """Real-time status (does not depend on the nightly cron)."""
        if inst.status == 'cancelled':
            return 'cancelled'
        if inst.due_amount <= 0.005:
            return 'paid'
        if inst.due_date and inst.due_date < today:
            return 'overdue'
        if inst.paid_amount > 0:
            return 'partially_paid'
        if inst.due_date == today:
            return 'due_today'
        return 'upcoming'

    @api.model
    def _agreement_payment_status(self, net_price, paid, has_overdue):
        if net_price - paid <= 0.01:
            return 'completed'
        if has_overdue:
            return 'overdue'
        if paid > 0:
            return 'in_progress'
        return 'not_started'

    def _add_lines(self, line_type, rows):
        Line = self.env['real.estate.portal.line'].sudo()
        vals = []
        for seq, row in enumerate(rows, start=1):
            row = dict(row, dashboard_id=self.id, line_type=line_type, sequence=seq)
            vals.append(row)
        if vals:
            Line.create(vals)

    def _build_commission(self, pid):
        """Commissions where this partner is the beneficiary (works for a
        customer who earns referral commission as well as for an agent)."""
        Commission = self.env['real.estate.commission'].sudo()
        commissions = Commission.search([('beneficiary_id', '=', pid), ('state', '!=', 'cancelled')],
                                        order='id desc')
        rows = []
        for c in commissions:
            agr = c.sale_agreement_id
            rate = ('%.2f%%' % c.rate_value) if c.calc_type == 'percentage' else _('Fixed')
            rows.append({
                'name': c.name,
                'ref': agr.name,
                'partner_name': c.customer_id.name,
                'project_name': c.project_id.project_name,
                'unit_name': c.unit_id.name,
                'text1': LEVEL_LABELS.get(c.level, c.level),
                'text2': c.agent_id.name or '',
                'text3': rate,
                'date': agr.agreement_date,
                'date2': c.payment_date,
                'amount': c.base_amount,
                'amount2': c.amount,
                'percent': c.rate_value if c.calc_type == 'percentage' else 0.0,
                'state_code': c.state,
                'state_label': COMMISSION_LABELS.get(c.state, c.state),
            })
        self._add_lines('commission', rows)
        total = sum(commissions.mapped('amount'))
        paid = sum(commissions.filtered(lambda c: c.state == 'paid').mapped('amount'))
        self.sudo().write({
            'commission_count': len(commissions),
            'commission_total': total,
            'commission_paid': paid,
            'commission_pending': total - paid,
            'commission_l1_total': sum(commissions.filtered(lambda c: c.level == '1').mapped('amount')),
            'commission_l2_total': sum(commissions.filtered(lambda c: c.level == '2').mapped('amount')),
        })

    # ==================================================================
    # Customer dashboard
    # ==================================================================
    def _build_customer(self):
        env = self.env
        pid = self.partner_id.id
        today = fields.Date.context_today(self)
        agreements = env['real.estate.sale.agreement'].sudo().search([
            ('customer_id', '=', pid), ('state', 'in', ('active', 'completed'))],
            order='agreement_date, id')
        collections = env['real.estate.collection'].sudo().search([
            ('customer_id', '=', pid), ('state', '=', 'confirmed'),
            ('sale_agreement_id', 'in', agreements.ids)], order='payment_date desc, id desc')
        installments = env['real.estate.installment'].sudo().search([
            ('plan_id.sale_agreement_id', 'in', agreements.ids),
            ('status', '!=', 'cancelled')], order='due_date, id')

        paid_by_agr, overdue_by_agr = {}, {}
        for col in collections:
            paid_by_agr[col.sale_agreement_id.id] = paid_by_agr.get(col.sale_agreement_id.id, 0.0) + col.amount

        # --- payment schedule ------------------------------------------
        schedule_rows, overdue_total = [], 0.0
        counts = {'paid': 0, 'pending': 0, 'overdue': 0}
        upcoming = []
        for inst in installments:
            state = self._installment_state(inst, today)
            agr = inst.plan_id.sale_agreement_id
            if state == 'overdue':
                overdue_total += inst.due_amount
                overdue_by_agr[agr.id] = overdue_by_agr.get(agr.id, 0.0) + inst.due_amount
                counts['overdue'] += 1
            elif state == 'paid':
                counts['paid'] += 1
            else:
                counts['pending'] += 1
                upcoming.append(inst)
            schedule_rows.append({
                'name': inst.milestone_name or _('Installment %s', inst.installment_number or '?'),
                'ref': agr.name,
                'project_name': inst.project_id.project_name,
                'unit_name': inst.unit_id.name,
                'date': inst.due_date,
                'amount': inst.amount,
                'amount2': inst.paid_amount,
                'amount3': inst.due_amount,
                'amount4': inst.late_fee_amount if state == 'overdue' else 0.0,
                'state_code': state,
                'state_label': INSTALLMENT_LABELS[state],
            })
        self._add_lines('schedule', schedule_rows)

        next_inst = upcoming[:1]
        # --- payments done ---------------------------------------------
        methods = dict(env['real.estate.collection']._fields['payment_method']._description_selection(env))
        payment_rows = []
        for col in collections:
            payment_rows.append({
                'name': col.name,
                'ref': col.installment_id.display_name if col.installment_id else _('Booking / Down payment / On account'),
                'project_name': col.project_id.project_name,
                'unit_name': col.unit_id.name,
                'text1': methods.get(col.payment_method, col.payment_method or ''),
                'text2': col.transaction_id or col.cheque_number or col.reference or '',
                'date': col.payment_date,
                'amount': col.amount,
                'state_code': 'paid',
                'state_label': _('Received'),
            })
        self._add_lines('payment', payment_rows)

        # --- properties -------------------------------------------------
        property_rows = []
        for agr in agreements:
            paid = paid_by_agr.get(agr.id, 0.0)
            status = self._agreement_payment_status(agr.net_price, paid, overdue_by_agr.get(agr.id, 0.0) > 0)
            nxt = installments.filtered(
                lambda i, a=agr: i.plan_id.sale_agreement_id == a and i in upcoming)[:1]
            property_rows.append({
                'name': agr.name,
                'project_name': agr.project_id.project_name,
                'unit_name': agr.unit_id.name,
                'date': agr.agreement_date,
                'date2': nxt.due_date if nxt else False,
                'amount': agr.net_price,
                'amount2': paid,
                'amount3': max(agr.net_price - paid, 0.0),
                'amount4': overdue_by_agr.get(agr.id, 0.0),
                'percent': agr.net_price and min(paid / agr.net_price * 100.0, 100.0) or 0.0,
                'state_code': status,
                'state_label': PAYMENT_STATUS_LABELS[status],
            })
        self._add_lines('property', property_rows)

        # --- expenses of the bought project(s) only ----------------------
        projects = agreements.mapped('project_id')
        allocations = env['real.estate.budget.allocation'].sudo().search([
            ('project_id', 'in', projects.ids),
            ('budget_id.state', 'in', ('approved', 'active', 'closed'))],
            order='project_id, budget_id, id')
        expense_rows, project_rows = [], []
        for project in projects:
            allocs = allocations.filtered(lambda a, p=project: a.project_id == p)
            budget = sum(allocs.mapped('allocated_amount'))
            committed = sum(allocs.mapped('committed_amount'))
            actual = sum(allocs.mapped('actual_amount'))
            project_rows.append({
                'name': project.project_name,
                'ref': project.name,
                'project_name': project.project_name,
                'text1': project.location or '',
                'date': project.planned_completion_date,
                'amount': budget,
                'amount2': committed,
                'amount3': actual,
                'amount4': budget - committed - actual,
                'percent': budget and (committed + actual) / budget * 100.0 or 0.0,
                'state_code': project.state,
                'state_label': self._selection_label(project, 'state'),
            })
        for alloc in allocations:
            expense_rows.append({
                'name': self._selection_label(alloc, 'budget_head'),
                'ref': alloc.budget_id.name,
                'project_name': alloc.project_id.project_name,
                'amount': alloc.allocated_amount,
                'amount2': alloc.committed_amount,
                'amount3': alloc.actual_amount,
                'amount4': alloc.remaining_amount,
                'percent': alloc.utilization_percentage,
            })
        self._add_lines('project', project_rows)
        self._add_lines('expense', expense_rows)
        exp_budget = sum(allocations.mapped('allocated_amount'))
        exp_committed = sum(allocations.mapped('committed_amount'))
        exp_actual = sum(allocations.mapped('actual_amount'))

        total_value = sum(agreements.mapped('net_price'))
        total_paid = sum(collections.mapped('amount'))
        self.sudo().write({
            'properties_count': len(agreements),
            'projects_count': len(projects),
            'total_value': total_value,
            'total_paid': total_paid,
            'total_due': max(total_value - total_paid, 0.0),
            'overdue_amount': overdue_total,
            'payment_progress': total_value and min(total_paid / total_value * 100.0, 100.0) or 0.0,
            'next_due_date': next_inst.due_date if next_inst else False,
            'next_due_amount': next_inst.due_amount if next_inst else 0.0,
            'installments_paid': counts['paid'],
            'installments_pending': counts['pending'],
            'installments_overdue': counts['overdue'],
            'exp_budget': exp_budget,
            'exp_committed': exp_committed,
            'exp_actual': exp_actual,
            'exp_remaining': exp_budget - exp_committed - exp_actual,
            'exp_utilization': exp_budget and (exp_committed + exp_actual) / exp_budget * 100.0 or 0.0,
        })
        self._build_commission(pid)

    # ==================================================================
    # Agent dashboard
    # ==================================================================
    def _build_agent(self):
        env = self.env
        pid = self.partner_id.id
        today = fields.Date.context_today(self)
        Agreement = env['real.estate.sale.agreement'].sudo()
        sales = Agreement.search([('agent_id', '=', pid), ('state', 'in', ('active', 'completed'))],
                                 order='agreement_date desc, id desc')
        referred = env['res.partner'].sudo().search([('referred_by_id', '=', pid)])
        customers = (referred | sales.mapped('customer_id')) - self.partner_id

        # --- all agreements / collections / installments of these customers
        cust_agreements = Agreement.search([
            ('customer_id', 'in', customers.ids), ('state', 'in', ('active', 'completed'))])
        collections = env['real.estate.collection'].sudo().search([
            ('customer_id', 'in', customers.ids), ('state', '=', 'confirmed'),
            ('sale_agreement_id', 'in', cust_agreements.ids)])
        installments = env['real.estate.installment'].sudo().search([
            ('plan_id.sale_agreement_id', 'in', cust_agreements.ids), ('status', '!=', 'cancelled')],
            order='due_date, id')

        paid_by_agr, paid_by_cust = {}, {}
        for col in collections:
            paid_by_agr[col.sale_agreement_id.id] = paid_by_agr.get(col.sale_agreement_id.id, 0.0) + col.amount
            paid_by_cust[col.customer_id.id] = paid_by_cust.get(col.customer_id.id, 0.0) + col.amount
        overdue_by_agr, overdue_by_cust, next_by_cust = {}, {}, {}
        for inst in installments:
            state = self._installment_state(inst, today)
            agr = inst.plan_id.sale_agreement_id
            if state == 'overdue':
                overdue_by_agr[agr.id] = overdue_by_agr.get(agr.id, 0.0) + inst.due_amount
                overdue_by_cust[agr.customer_id.id] = overdue_by_cust.get(agr.customer_id.id, 0.0) + inst.due_amount
            elif state in ('upcoming', 'due_today', 'partially_paid'):
                next_by_cust.setdefault(agr.customer_id.id, inst.due_date)

        # --- customer rows -----------------------------------------------
        customer_rows, total_overdue = [], 0.0
        for cust in customers.sorted('name'):
            c_agrs = cust_agreements.filtered(lambda a, c=cust: a.customer_id == c)
            value = sum(c_agrs.mapped('net_price'))
            paid = paid_by_cust.get(cust.id, 0.0)
            overdue = overdue_by_cust.get(cust.id, 0.0)
            total_overdue += overdue
            if not c_agrs:
                status, label = 'not_started', _('No purchase yet')
            else:
                status = self._agreement_payment_status(value, paid, overdue > 0)
                label = PAYMENT_STATUS_LABELS[status]
            customer_rows.append({
                'name': cust.name,
                'text1': cust.mobile or cust.phone or '',
                'text2': cust.email or '',
                'text3': _('Referred by me') if cust in referred else _('Sold by me'),
                'project_name': ', '.join(c_agrs.mapped('project_id.project_name')),
                'unit_name': ', '.join(c_agrs.mapped('unit_id.name')),
                'date2': next_by_cust.get(cust.id),
                'amount': value,
                'amount2': paid,
                'amount3': max(value - paid, 0.0),
                'amount4': overdue,
                'percent': value and min(paid / value * 100.0, 100.0) or 0.0,
                'state_code': status,
                'state_label': label,
            })
        self._add_lines('customer', customer_rows)

        # --- my sales + my commission on each -----------------------------
        my_commissions = env['real.estate.commission'].sudo().search([
            ('beneficiary_id', '=', pid), ('state', '!=', 'cancelled')])
        sale_rows = []
        for agr in sales:
            paid = paid_by_agr.get(agr.id, 0.0)
            status = self._agreement_payment_status(agr.net_price, paid, overdue_by_agr.get(agr.id, 0.0) > 0)
            mine = my_commissions.filtered(lambda c, a=agr: c.sale_agreement_id == a)
            sale_rows.append({
                'name': agr.name,
                'partner_name': agr.customer_id.name,
                'project_name': agr.project_id.project_name,
                'unit_name': agr.unit_id.name,
                'date': agr.agreement_date,
                'amount': agr.net_price,
                'amount2': paid,
                'amount3': max(agr.net_price - paid, 0.0),
                'amount4': sum(mine.mapped('amount')),
                'percent': agr.net_price and min(paid / agr.net_price * 100.0, 100.0) or 0.0,
                'state_code': status,
                'state_label': PAYMENT_STATUS_LABELS[status],
            })
        self._add_lines('sale', sale_rows)

        # --- CRM follow-ups ------------------------------------------------
        Lead = env['real.estate.agent.lead'].sudo()
        open_leads = Lead.search([('agent_id', '=', pid), ('stage', 'not in', ('won', 'lost'))])
        followups = open_leads.filtered('next_followup_date').sorted('next_followup_date')[:30]
        follow_rows = []
        for lead in followups:
            if lead.next_followup_date < today:
                code, label = 'overdue', _('Overdue')
            elif lead.next_followup_date == today:
                code, label = 'due_today', _('Today')
            else:
                code, label = 'upcoming', _('Upcoming')
            follow_rows.append({
                'name': lead.name,
                'partner_name': lead.contact_name or lead.partner_id.name or '',
                'text1': lead.phone or '',
                'text2': STAGE_LABELS.get(lead.stage, lead.stage),
                'project_name': lead.project_id.project_name,
                'unit_name': lead.unit_id.name,
                'date': lead.next_followup_date,
                'amount': lead.expected_value,
                'state_code': code,
                'state_label': label,
            })
        self._add_lines('followup', follow_rows)

        total_value = sum(sales.mapped('net_price'))
        total_paid = sum(paid_by_agr.get(a.id, 0.0) for a in sales)
        self.sudo().write({
            'customers_count': len(customers),
            'sales_count': len(sales),
            'total_value': total_value,
            'total_paid': total_paid,
            'total_due': max(total_value - total_paid, 0.0),
            'overdue_amount': total_overdue,
            'payment_progress': total_value and min(total_paid / total_value * 100.0, 100.0) or 0.0,
            'open_leads': len(open_leads),
            'followups_due': len(open_leads.filtered(
                lambda l: l.next_followup_date and l.next_followup_date <= today)),
            'won_leads': Lead.search_count([('agent_id', '=', pid), ('stage', '=', 'won')]),
            'pipeline_value': sum(open_leads.mapped('expected_value')),
        })
        self._build_commission(pid)
