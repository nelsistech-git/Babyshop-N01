# Daily Sale & Official Cost Report — Odoo 17

Fully automated version of your "Daily Sale & Official Cost" sheet. Every
number is pulled live from posted `account.move` / `account.move.line` /
`account.payment` records — nothing is typed in by hand.

## Install
1. Copy the `daily_sale_official_cost` folder into your Odoo 17 addons path.
2. Restart the server, then Apps → Update Apps List.
3. Search "Daily Sale & Official Cost" and Install.
4. Menu: **Accounting → Reporting → Daily Sale & Official Cost**.

## One-time setup
Open the report form and set **Management / MD Partners** (or set it once
under the company record). Any outbound payment to those partners is
reported as "MD Sir Cash Paid" instead of an ordinary supplier payment.

## How each section maps to accounting data
| Section | Source | Filter |
|---|---|---|
| Showroom Sale | `account.move` | `move_type='out_invoice'`, posted, `invoice_date` = selected date |
| Official Cost | `account.move.line` | posted journal entries, expense accounts, debit lines |
| Supplier Transaction | `account.payment` | outbound, `partner_type='supplier'` |
| Mobile & Bank | `account.payment` | inbound, `partner_type='customer'`, bank/cash journal (bKash detected by journal name) |

## Reconciliation formula
```
Current Office Cash =
    (Net Office Cash Adjustment + Total Amount Tk.)
  - (MD Sir Cash Paid + Total Official Cost + Total Paid to Suppliers)
```
`Net Office Cash Adjustment` is pulled automatically from **yesterday's**
`Current Office Cash` — you never re-type the opening balance.

**Note on your sample sheet:** the sample's final `Net Office Cash` formula
(`G26-G29-C14-G28`) dropped `Total Amount Tk.` (bank/bKash collections)
entirely — that's exactly the kind of manual-formula slip this automation
removes. This module always includes all four components, and also nets
out supplier payments made *to management partners* so they aren't double
counted as both "MD Sir Cash Paid" and "Supplier Transaction."　If you'd
rather match the sheet's original (unfixed) formula exactly, tell me and
I'll adjust `_compute_totals` in `models/daily_report.py`.

## Locking (Requirement: Transaction Locking)
- **Lock Report** freezes today's lines so later edits to historical
  journal entries can never change an already-issued report.
- **Unlock** is restricted to the Accounting Manager group.

## Real-time sync (Requirement: Real-time Synchronization)
`account.move.action_post` and `account.payment.action_post` are extended
to automatically refresh any *draft* (unlocked) report dated the same day
as soon as a new entry is validated — no manual refresh needed. A
**Refresh from Ledger** button is also available for a manual pull.

## Currency / rounding (Requirement: Currency Precision)
All amount fields use `fields.Monetary` tied to `company_id.currency_id`,
so every figure automatically respects the currency's configured
`decimal_precision` — no separate rounding logic needed.

## Printable report
A matching PDF (Print button on the form, or Reporting menu) reproduces
the two-column layout of your original sheet plus the bottom summary
panel.
