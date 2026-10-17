# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

PREFIX = 'NBD-TEST-'


@tagged('post_install', '-at_install', 'nelsis_bond_dashboard')
class TestBondDashboard(TransactionCase):
    """Uses res.partner as a neutral fixture so tests do not depend on
    field names of other Nelsis modules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        cls.g_store = ref('nelsis_bond_dashboard.group_bond_dash_storekeeper')
        cls.g_audit = ref('nelsis_bond_dashboard.group_bond_dash_auditor')
        cls.g_admin = ref('nelsis_bond_dashboard.group_bond_dash_admin')
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.u_store = Users.create({'name': 'NBD Store', 'login': 'nbd_store', 'email': 'nbd_store@example.com',
                                    'groups_id': [(6, 0, [cls.g_store.id])]})
        cls.u_audit = Users.create({'name': 'NBD Audit', 'login': 'nbd_audit', 'email': 'nbd_audit@example.com',
                                    'groups_id': [(6, 0, [cls.g_audit.id])]})
        cls.u_admin = ref('base.user_admin')
        cls.today = fields.Date.context_today(cls.env['res.users'])
        Partner = cls.env['res.partner']
        cls.p_past = Partner.create({'name': PREFIX + 'past', 'date': cls.today - timedelta(days=1), 'color': 2})
        cls.p_soon = Partner.create({'name': PREFIX + 'soon', 'date': cls.today + timedelta(days=5), 'color': 3})
        cls.p_far = Partner.create({'name': PREFIX + 'far', 'date': cls.today + timedelta(days=200), 'color': 0})
        cls.Kpi = cls.env['bond.dashboard.kpi']

    def _kpi(self, **vals):
        base = {'name': 'NBD card', 'model_name': 'res.partner',
                'domain': "[('name', 'like', '%s')]" % PREFIX}
        base.update(vals)
        return self.Kpi.create(base)

    def _cards(self, user):
        data = self.env['bond.dashboard'].with_user(user).get_dashboard_data()
        return {c['name']: c for s in data['sections'] for c in s['cards']}

    # ---- data accuracy -------------------------------------------------
    def test_count_sum_ratio_breakdown_accuracy(self):
        count = self._kpi(name='NBD count')._evaluate()
        self.assertEqual(count['status'], 'ok')
        self.assertEqual(count['value'], 3)
        total = self._kpi(name='NBD sum', kpi_type='sum', measure_field='color')._evaluate()
        self.assertEqual(total['value'], 5)
        ratio = self._kpi(name='NBD ratio', kpi_type='ratio', measure_field='color',
                          denominator_field='color')._evaluate()
        self.assertAlmostEqual(ratio['value'], 100.0)
        rows = self._kpi(name='NBD breakdown', kpi_type='breakdown', groupby_field='type',
                         measure_field='color')._evaluate()
        self.assertEqual(rows['status'], 'ok')
        self.assertEqual(sum(r['value'] for r in rows['rows']), 5)

    def test_domain_with_date_helpers_counts_expired(self):
        card = self._kpi(name='NBD expired', domain=(
            "[('name', 'like', '%s'), ('date', '<', today)]" % PREFIX))._evaluate()
        self.assertEqual(card['value'], 1)

    def test_bad_configuration_is_reported_not_raised(self):
        self.assertEqual(self._kpi(name='NBD bad', domain="[('no_such_field', '=', 1)]")._evaluate()['status'], 'error')
        self.assertEqual(self._kpi(name='NBD syntax', domain='[(')._evaluate()['status'], 'error')
        self.assertEqual(self._kpi(name='NBD nomodel', model_name='x.y.z')._evaluate()['status'], 'unavailable')

    # ---- role-based visibility ----------------------------------------
    def test_card_visibility_by_group(self):
        self._kpi(name='NBD audit only', group_ids=[(6, 0, [self.g_audit.id])])
        self._kpi(name='NBD everyone')
        self.assertNotIn('NBD audit only', self._cards(self.u_store))
        self.assertIn('NBD everyone', self._cards(self.u_store))
        self.assertIn('NBD audit only', self._cards(self.u_audit))
        self.assertIn('NBD audit only', self._cards(self.u_admin))

    def test_unconfigured_cards_hidden_from_non_admins(self):
        self._kpi(name='NBD broken', domain='[(')
        self.assertNotIn('NBD broken', self._cards(self.u_store))
        self.assertEqual(self._cards(self.u_admin)['NBD broken']['status'], 'error')

    def test_user_without_role_is_refused(self):
        outsider = self.env['res.users'].with_context(no_reset_password=True).create(
            {'name': 'NBD out', 'login': 'nbd_out', 'email': 'nbd_out@example.com'})
        with self.assertRaises(AccessError):
            self.env['bond.dashboard'].with_user(outsider).get_dashboard_data()

    def test_alert_record_rule(self):
        alert = self.env['bond.dashboard.alert'].log_unauthorized_attempt('stock.move', 1, 'rule test')
        alert = self.env['bond.dashboard.alert'].browse(alert)
        alert.sudo().recipient_user_ids = [(6, 0, [self.u_audit.id])]
        with self.assertRaises(AccessError):
            alert.with_user(self.u_store).read(['name'])
        self.assertTrue(alert.with_user(self.u_audit).read(['name']))

    def test_auditor_is_read_only_on_stock_history(self):
        for model in ('stock.move.line', 'stock.move', 'stock.picking'):
            Model = self.env[model].with_user(self.u_audit)
            self.assertTrue(Model.check_access_rights('read', raise_exception=False), model)
            for mode in ('write', 'create', 'unlink'):
                self.assertFalse(Model.check_access_rights(mode, raise_exception=False), '%s %s' % (model, mode))

    # ---- alerts, reminders, expired records ---------------------------
    def _rule(self, **vals):
        base = {'name': 'NBD rule', 'alert_type': 'license_expiry', 'model_name': 'res.partner',
                'domain': "[('name', 'like', '%s')]" % PREFIX, 'date_field': 'date', 'lead_days': 10,
                'group_ids': [(6, 0, [self.g_audit.id])]}
        base.update(vals)
        return self.env['bond.dashboard.alert.rule'].create(base)

    def test_expiry_rule_creates_alerts_activities_and_dedups(self):
        rule = self._rule()
        created = rule._run()
        self.assertEqual(len(created), 2)  # expired + within lead window; far date excluded
        self.assertEqual(set(created.mapped('res_id')), {self.p_past.id, self.p_soon.id})
        self.assertIn(self.u_audit, created.mapped('activity_ids.user_id'))
        self.assertFalse(rule._run(), 'a second run must not duplicate open alerts')
        self.assertEqual(rule.last_match_count, 2)

    def test_alert_auto_resolves_when_condition_clears(self):
        rule = self._rule()
        rule._run()
        self.p_past.date = self.today + timedelta(days=100)
        rule._run()
        Alert = self.env['bond.dashboard.alert']
        resolved = Alert.search([('rule_id', '=', rule.id), ('state', '=', 'resolved')])
        self.assertEqual(resolved.mapped('res_id'), [self.p_past.id])
        self.assertTrue(resolved.auto_resolved)
        self.assertEqual(Alert.search_count([('rule_id', '=', rule.id), ('state', '!=', 'resolved')]), 1)

    def test_ratio_threshold_rule(self):
        self.p_past.color, self.p_soon.color = 9, 5
        rule = self._rule(alert_type='entitlement_threshold', date_field=False,
                          ratio_numerator_field='color', ratio_denominator_field='id', threshold_percent=0.0)
        self.assertTrue(rule._find_matches())
        rule.threshold_percent = 100000.0
        self.assertFalse(rule._find_matches())

    def test_broken_rule_records_error_and_does_not_crash_cron(self):
        rule = self._rule(domain='[(')
        self.assertFalse(rule._run())
        self.assertTrue(rule.last_error)
        self.env['bond.dashboard.alert.rule']._cron_run_rules()

    def test_cron_is_scheduled(self):
        cron = self.env.ref('nelsis_bond_dashboard.ir_cron_bond_alert_rules')
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, 'bond.dashboard.alert.rule')
        self.assertEqual((cron.interval_number, cron.interval_type), (1, 'days'))

    def test_unauthorized_attempt_logged_and_counted(self):
        alert_id = self.env['bond.dashboard.alert'].log_unauthorized_attempt('stock.picking', 7, 'blocked')
        alert = self.env['bond.dashboard.alert'].browse(alert_id)
        self.assertEqual((alert.alert_type, alert.severity, alert.state), ('unauthorized_attempt', 'critical', 'open'))
        card = self._cards(self.u_admin)['Open Unauthorized Attempts']
        self.assertEqual(card['value'], self.env['bond.dashboard.alert'].search_count(
            [('state', '!=', 'resolved'), ('alert_type', '=', 'unauthorized_attempt')]))

    # ---- audit protection ---------------------------------------------
    def test_resolve_needs_note_and_only_resolved_can_be_deleted(self):
        alert = self.env['bond.dashboard.alert'].browse(
            self.env['bond.dashboard.alert'].log_unauthorized_attempt('stock.move', 1, 'x'))
        with self.assertRaises(UserError):
            alert.action_resolve()
        with self.assertRaises(UserError):
            alert.unlink()
        alert.resolution_note = 'Checked with warehouse manager'
        alert.action_resolve()
        self.assertEqual(alert.state, 'resolved')
        alert.unlink()
