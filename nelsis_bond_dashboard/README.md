# nelsis_bond_dashboard (Odoo Community 17)

Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.

Module 07 of the Nelsis Bond Warehouse system: dashboard, alerts and audit access.

## Dependencies
`base`, `mail`, `stock`, `nelsis_bond_warehouse` (main addon named in the Master Prompt; confirm it
defines the `bond.warehouse.*` models). No external Python packages. No SMS/WhatsApp.

## Install
1. Back up the database and filestore.
2. Copy `nelsis_bond_dashboard` into the addons path; restart Odoo.
3. Apps > Update Apps List > install "Nelsis Bond Dashboard, Alerts & Audit"
   (or `odoo -d DB -i nelsis_bond_dashboard --stop-after-init`).
4. Assign each user ONE Bond Dashboard role group (Settings > Users). Operational roles must also hold
   the stock / contract groups they need for their daily work; these groups only govern this module.
5. Verify every default card (Bond Dashboard > Configuration > Dashboard Cards > Test Card) and every
   alert rule (Preview Matches) against the approved contract field names, then activate the rules.

## Test
`odoo -d TESTDB -i nelsis_bond_dashboard --test-tags /nelsis_bond_dashboard --stop-after-init`
Then run the existing LC module's own tests as regression.

## Upgrade / rollback
Upgrade: `-u nelsis_bond_dashboard`. Rollback: restore the backup, or uninstall the module (alert log,
rules and cards are removed; stock and bond records are untouched).

## Design notes
* Cards are computed live with the current user's rights; nothing is cached or duplicated.
* Alerts point at source records. Open alerts cannot be deleted. Auditors have read-only access.
* Other modules can log blocked actions: `env['bond.dashboard.alert'].log_unauthorized_attempt(model, id, reason)`.
* Renewal-review window: system parameter `nelsis_bond_dashboard.renewal_review_days` (default 90, a
  placeholder, not a legal period). No legal limits are embedded.
