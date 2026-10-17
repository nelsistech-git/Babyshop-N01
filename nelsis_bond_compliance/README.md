# Nelsis Bond Compliance (Odoo 17) — Module 01

Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed. License: LGPL-3 (change in `__manifest__.py` if a different license is intended).

## Install
1. Copy the folder `nelsis_bond_compliance` into an addons path (back up the database first).
2. Restart Odoo, enable developer mode, Apps → Update Apps List.
3. Install **Nelsis Bond Compliance**, or: `odoo-bin -d <db> -i nelsis_bond_compliance --stop-after-init`
4. Assign roles under Settings → Users → *Bond Compliance* (Officer / Reviewer / Approver / Manager). Administrators receive Manager.

## Test
`odoo-bin -d <test_db> -i nelsis_bond_compliance --test-tags /nelsis_bond_compliance --stop-after-init`

## Upgrade / rollback
Upgrade: `-u nelsis_bond_compliance`. Rollback: restore the database backup and the previous addon folder.
Uninstalling removes the rule register, exceptions and evaluation log — do not uninstall on a database with audit history.

See `docs/technical_contract.md` for models, security, workflow and the evaluation interface (draft, pending approval).
