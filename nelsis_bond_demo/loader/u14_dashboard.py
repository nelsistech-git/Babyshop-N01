# -*- coding: utf-8 -*-
"""Dashboard alerts: switch on the shipped alert rules (quiet: no mail, no activities),
evaluate them against the demo data and work some alerts through their lifecycle."""
from odoo.exceptions import AccessError

RULES = ['rule_license_expiry', 'rule_security_expiry', 'rule_missing_document',
         'rule_pending_verification', 'rule_reconciliation_discrepancy',
         'rule_entitlement_threshold', 'rule_outstanding_approval', 'rule_unauthorized_attempt']
NS = 'nelsis_bond_dashboard.'


def run(ctx):
    env = ctx.env

    def activate():
        for xml in RULES:
            rule = env.ref(NS + xml, raise_if_not_found=False)
            if rule:
                rule.sudo().write({'active': True, 'notify_message': False, 'notify_activity': False})

    def evaluate():
        for xml in RULES:
            rule = env.ref(NS + xml, raise_if_not_found=False)
            if rule and rule.model_name:
                rule.sudo()._run()

    def unauthorized():
        picking = ctx.need('receipt_a1').picking_id
        env['bond.dashboard.alert'].sudo().log_unauthorized_attempt(
            'stock.picking', picking.id,
            'Demo: a store user tried to change the bond references of a validated receipt.',
            user_id=ctx.user('store').id)

    def lifecycle():
        Alert = env['bond.dashboard.alert'].sudo()
        alerts = Alert.search([('state', '=', 'open')], order='id')
        to_ack, to_resolve = alerts[:3], alerts[3:5]
        actor = ctx.user('manager')
        for alert in to_ack:
            try:
                with env.cr.savepoint():
                    alert.with_user(actor).action_acknowledge()
            except AccessError:
                alert.action_acknowledge()
        for alert in to_resolve:
            alert.write({'resolution_note': 'Demo: reviewed and handled by the bond operations manager.'})
            alert.action_resolve()

    ctx.step('dashboard.activate_rules', activate)
    ctx.step('dashboard.evaluate_rules', evaluate)
    ctx.step('dashboard.unauthorized_attempt', unauthorized)
    ctx.step('dashboard.alert_lifecycle', lifecycle)
