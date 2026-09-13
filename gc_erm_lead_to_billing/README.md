# Grameen Cybernet ERM — Lead to Billing

`gc_erm_lead_to_billing` — a business-process layer on top of **Odoo Community 17**
implementing the SRS *"Grameen Cybernet ERM — Lead to Billing System" v1.0*.

The module does **not** replace Odoo's CRM, Sales, Inventory, Purchase or
Accounting. It adds the controlled workflow on top and lets the standard Odoo
records stay the source of truth for their own domain (SRS §95).

---

## 1. Installation

### Requirements

* Odoo Community 17.0
* PostgreSQL 12+
* Standard apps (installed automatically as dependencies):
  `base, mail, contacts, crm, sale_management, stock, purchase, account,
  project, board`

### Steps

1. Copy the `gc_erm_lead_to_billing` folder into your Odoo addons path,
   for example:

   ```bash
   cp -r gc_erm_lead_to_billing /opt/odoo/custom-addons/
   chown -R odoo:odoo /opt/odoo/custom-addons/gc_erm_lead_to_billing
   ```

2. Make sure the folder is listed in `addons_path` in `odoo.conf`:

   ```ini
   addons_path = /opt/odoo/addons,/opt/odoo/custom-addons
   ```

3. Restart Odoo and update the apps list:

   ```bash
   sudo systemctl restart odoo
   ```

4. In Odoo: **Apps → Update Apps List**, search for
   *"Grameen Cybernet ERM"* and click **Activate**.

   Or from the command line:

   ```bash
   odoo -c /etc/odoo/odoo.conf -d YOURDB -i gc_erm_lead_to_billing --stop-after-init
   ```

5. Upgrade later with:

   ```bash
   odoo -c /etc/odoo/odoo.conf -d YOURDB -u gc_erm_lead_to_billing --stop-after-init
   ```

### Run the test suite

```bash
odoo -c /etc/odoo/odoo.conf -d TESTDB -i gc_erm_lead_to_billing \
     --test-enable --test-tags=/gc_erm_lead_to_billing --stop-after-init
```

97 tests cover the 13 UAT scenarios, the costing formulas, the workflow
guards, the record rules and the access rights.

---

## 2. First-time configuration

Everything below lives under **Grameen ERM → Configuration**
(visible to the *ERM Administrator* group).

| Step | Where | What to do |
|------|-------|------------|
| 1 | Settings → Users | Assign each user one ERM role (see §3) |
| 2 | Master Data → Service Catalog | Review the 5 starter services; set *survey required*, *installation required*, *billing policy* and *margin* per service |
| 3 | Master Data → Teams | Create your technical and implementation teams with their members |
| 4 | Process → Installation Checklists | Adjust the 13-item default checklist |
| 5 | Process → Approval Matrix | Set the BDT approval bands (defaults follow SRS §60) |
| 6 | Settings | Segregation of duties, technical review, default margin, proposal validity, SLA days |
| 7 | Settings → Technical → Sequences | Change document prefixes if needed (`GC-LEAD-`, `GC-SUR-`, …) |

---

## 3. Security roles (SRS §7)

| Group | Can do | Cannot do |
|-------|--------|-----------|
| **ERM User** | Read configuration + audit trail | — |
| **Sales User** | Create/submit leads, create surveys, prepare proposals | Approve own lead or proposal, edit approved costing |
| **Sales HOD** | Everything Sales does + approve/reject/revise leads and proposals, see all sales records | Approve a document they submitted (unless segregation is off) |
| **Technical User** | Perform surveys, build BOQ + costing, submit technical reports | Create leads or proposals |
| **Technical Manager** | Review/approve technical reports, see all technical records | — |
| **Implementation User** | Execute work orders, record installations, submit installation reports | Approve commercial documents |
| **ERM Inventory User** | Check stock, reserve, process deliveries | — |
| **ERM Purchase User** | Process procurement requests, create RFQs/POs | — |
| **ERM Accounts User** | Create/post invoices, follow payments | Change operational documents |
| **ERM Management** | Read everything, dashboards, reports | Write anything |
| **ERM Administrator** | Full access, unlock documents, purge audit entries | — |

Record rules (SRS §68) additionally limit each role to its own records:
a sales rep sees only their own leads, an engineer only their assigned surveys,
an implementation user only their assigned work orders. HOD, managers and
management see everything in their scope.

---

## 4. The end-to-end process

```
Lead (GC-LEAD-)                     Sales creates → submits
   └── HOD Approval                 approve / reject / request revision
        └── Survey (GC-SUR-)        generated from the approved lead
             ├── assignment          team, engineer, date, deadline
             ├── technical survey    availability, feasibility, GPS
             └── BOQ (GC-BOQ-)      costing + margin, version controlled
                  └── Technical Report (GC-TR-)   → locks the BOQ
                       └── Proposal (GC-PROP-)    versioned, HOD approved
                            └── Quotation         standard sale.order
                                 └── Sales Order  customer acceptance
                                      └── Work Order (GC-WO-)
                                           ├── inventory check
                                           ├── Procurement (GC-PR-) → RFQ → PO → Receipt
                                           ├── Delivery (stock.picking)
                                           ├── Installation (GC-INS-) + checklist
                                           │    └── Revisit (new visit, old report kept)
                                           └── Invoice (account.move) → Payment
```

### Key control points

* **BR-001** A survey cannot be created before the lead is approved.
* **BR-002** Only Sales HOD approves leads.
* **BR-004** Technical costing must exist before proposal approval.
* **BR-005** An approved proposal cannot be silently edited — use *Create Revision*.
* **BR-006** Customer acceptance (confirmed sales order) is required before the work order.
* **BR-007** A material shortage generates a procurement request.
* **BR-008** An installation always references a work order.
* **BR-009** A successful installation is required for final billing (unless the policy says otherwise).
* **BR-010** Every approval/rejection is written to the audit trail.

---

## 5. Costing formulas (SRS §18)

Per BOQ line:

```
Material Cost      = Quantity × Unit Cost
Line Internal Cost = Material + Installation + Transport + Other
```

Margin, per the configured method:

| Method | Formula |
|--------|---------|
| Fixed Amount | `margin = value` |
| Percentage on Cost | `margin = cost × value / 100` |
| Percentage on Selling Price | `margin = cost × value / (100 − value)` |

```
Unit Sales Price = (Line Cost + Margin) / Quantity      (6 decimals internally)
Subtotal         = Unit Price × Qty × (1 − discount%)   then taxes
```

The unit price is stored with six decimals so that "cost + margin" ties out
exactly on large quantities; the customer-facing quotation and invoice round
it to the currency precision, exactly like standard Odoo.

---

## 6. Billing policies (SRS §41 / §43)

| Policy | Billing allowed when |
|--------|----------------------|
| Full Billing on Installation | a successful installation report exists |
| Advance + Final | advance immediately, final after installation |
| Advance (100%) | as soon as the order is confirmed |
| Delivery Based | the delivery is done |
| Milestone | 30/40/30 style split, configurable per service and per work order |
| Recurring | reserved for a later phase |

The policy is proposed from the service catalog and can be overridden per
work order.

---

## 7. Dashboards and reporting

* **Dashboards** (Grameen ERM → Dashboards): Management, Sales, Technical,
  Implementation, Inventory and Finance. Built entirely from native Odoo
  views on a `board.board` page — **no custom JavaScript**, so nothing breaks
  when Odoo is patched.
* **Reporting**: lead pipeline, proposal win/loss, feasibility, costing
  analysis, implementation by team, engineer performance, revenue, audit trail.
* **12 printable PDFs**: Lead Summary, Survey Form, Technical Survey Report,
  BOQ, Technical Costing (internal only), Technical Report, Commercial
  Proposal, Work Order, Material Requirement, Procurement Request,
  Installation Report, Revisit Report.

---

## 8. Automation

Six scheduled jobs (Settings → Technical → Scheduled Actions), all daily:

| Job | Purpose |
|-----|---------|
| Survey deadline check | flags overdue surveys, notifies the engineer |
| Proposal expiry | marks expired proposals, asks Sales to follow up |
| Work order delay check | flags delayed work orders |
| Procurement aging | chases overdue procurement |
| Installation aging | chases pending installations |
| Overdue invoice reminder | *inactive by default* — enable it once your outgoing mail server is configured |

17 mail templates cover the notification list of SRS §56 and are editable
under Settings → Technical → Email Templates.

---

## 9. Notes for maintainers

* All business rules are implemented in Python (`models/`), never only in XML,
  so they cannot be bypassed through the UI or the API.
* `gc.erm.document.mixin` centralises sequences, the audit trail, chatter,
  SLA and the approval guards for every document.
* State changes go through a single method, `_gc_transition()`, which enforces
  the allowed source states and writes the history entry.
* The audit trail (`gc.erm.status.history`) is append-only for regular users.
* No Odoo core file is modified; everything is inheritance and extension.
* Editable computed fields each have their own compute method — grouping one
  with a read-only field makes Odoo skip the whole group when the value is
  supplied (which happens on `copy()`), silently zeroing the read-only field.

---

## 10. Backup (SRS §87)

Not covered by the module itself. Recommended production setup:

```bash
# daily 02:00
pg_dump -Fc YOURDB > /backup/db/YOURDB_$(date +%F).dump
tar czf /backup/filestore/filestore_$(date +%F).tgz ~/.local/share/Odoo/filestore/YOURDB
```

Keep daily for 14 days, weekly for 8 weeks, monthly for 12 months, copy
off-server, and test a restore every quarter.
