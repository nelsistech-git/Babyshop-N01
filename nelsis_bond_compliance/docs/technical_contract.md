# nelsis_bond_compliance — Technical Contract (Module 01)

Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
Target: Odoo Community 17.0. Depends: `base`, `mail`. No dependency on the LC module or Inventory.

## Models
| Model | Purpose |
|---|---|
| `bond.compliance.rule` | Versioned regulatory rule (proposed fields + `version`, `submitted_*`, `rejection_reason`, professional-verification fields, `next_review_date`) |
| `bond.compliance.rule.parameter` | Validation parameter lines (`key`, `value_type`, `operator`, typed value, `value_is_set`, `is_statutory`, `source_note`) |
| `bond.compliance.rule.category` | Rule categories (master data) |
| `bond.compliance.license.category` | License / factory categories (explicit applicability) |
| `bond.compliance.document.type` | Required-document types |
| `bond.compliance.exception` | Time-boxed, approved compliance exceptions (sequence `bond.compliance.exception`, `BCE/%(year)s/0001`) |
| `bond.compliance.evaluation` | Immutable evaluation log (keeps rule version used) |
| `bond.compliance.engine` | AbstractModel — evaluation interface for other modules |
| `bond.compliance.reject.wizard` | Transient — rejection reason |

### Deviations from the proposed field list (to be approved)
| Proposed | Implemented | Reason |
|---|---|---|
| `rule_category` | `rule_category_id` (Many2one) | Configurable categories |
| `parameter_definition` | `parameter_ids` (One2many) | Typed, individually sourced parameters |
| `required_document_types` | `required_document_type_ids` (Many2many) | Relational |
| `verification_status` | Selection: draft, under_review, reviewed, approved, active, superseded, rejected | Workflow + supersession |
| `active` | Odoo archive flag only | Activation is the `active` *status*, so a drafted rule is never "in force" |
| (new) `applicable_category_ids` | Many2many to license category | `applicability` stays as free-text notes |

## State machine (`verification_status`)
`draft → under_review → reviewed → approved → active → superseded`; `under_review|reviewed → rejected`;
`under_review|reviewed|rejected → draft`. Only workflow methods change status (context key `bond_compliance_workflow`).

## Security group XML IDs
`group_bond_compliance_user` (read) · `_officer` (draft/submit/new version) · `_reviewer` (review, reject, record professional verification) ·
`_approver` (approve, activate, change end date, approve exceptions) · `_manager` (implies officer+reviewer+approver; master data).
Segregation of duties (submitter ≠ reviewer ≠ approver; exception requester ≠ approver) is enforced while
`ir.config_parameter` `nelsis_bond_compliance.enforce_segregation` = `True`.

## Menu / action XML IDs
Menus: `menu_bond_compliance_root`, `_rules`, `_exceptions`, `_evaluations`, `_config`, `_rule_categories`, `_license_categories`, `_document_types`.
Actions: `action_bond_compliance_rule`, `_exception`, `_evaluation`, `_rule_category`, `_license_category`, `_document_type`.

## Evaluation interface — DRAFT, API 1.0-draft, pending approval
```python
engine = env['bond.compliance.engine']
rule  = engine.get_applicable_rule(code, on_date=None, license_category=None)   # recordset (0 or 1)
rules = engine.get_applicable_rules(code, on_date=None, license_category=None)
res   = engine.evaluate(code, on_date=None, license_category=None, values=None,
                        documents=None, res_model=None, res_id=None, reference=None, log=True)
rule.get_parameter_value(key, default=None)
```
`license_category`: code string, id or record. `values`: `{parameter_key: actual}`. `documents`: iterable of document-type codes or records.

Result keys: `status` (`passed|failed|no_rule|ambiguous`), `passed`, `rule_id`, `rule_version`, `official_reference`, `source_url`,
`requires_professional_verification`, `parameter_results[]`, `missing_document_types[]`, `messages[]`, `exception_ids[]`,
`covered_by_exception`, `evaluation_id`, `disclaimer`.

Semantics: only `active`/`superseded` rules are selectable; the transaction date picks the version; superseded versions
stay selectable for the dates they were in force; `no_rule` is never a pass; an approved exception never converts `failed`
to `passed`; each logged evaluation keeps `rule_id` + `rule_version`. Callers must store `evaluation_id` on their documents.

## Regulatory source matrix
This addon seeds **no** rules or statutory values. Each rule must be entered from the official sources
(https://nbr.gov.bd/regulations/sros/customs-sros/eng, https://bangladeshcustoms.gov.bd/relevant/bonded_warehouse)
with: official reference, URL, publication/effective dates, applicable license category, required documents,
parameters with source clause, reviewer and approver. Research of the current (incl. 2026 amended) texts and
interpretation by a qualified Bangladesh customs professional are still required.

## Technical parameters (Settings → Technical → System Parameters)
`nelsis_bond_compliance.enforce_segregation` (default `True`), `nelsis_bond_compliance.expiry_warning_days` (default `30`).

## Scheduled actions
`Bond Compliance: Rule Reminders` (expiring/expired rules, re-verification due, pending legal verification) and
`Bond Compliance: Expire Exceptions`; both daily.
