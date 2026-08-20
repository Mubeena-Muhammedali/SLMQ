{
    "name": "Partial Reconcile - Move to Account",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Move part of a residual balance to a chosen account/journal "
                "while keeping the remainder open for future reconciliation.",
    "description": """
Partial Reconcile - Move to Account
====================================

Adds a safe, additive action (does not modify any existing Odoo core
reconciliation logic) available from the *Actions* menu on the
"Journal Items to reconcile" list (Accounting > Customer/Vendor
Payments > any partner drill-down, or Accounting > Actions > Reconcile).

What it does
------------
1. You select the Accounts Receivable / Payable line(s) you want to
   partially settle (exactly as you do today before clicking
   "Reconcile").
2. Instead of clicking "Reconcile", open Actions > "Partial Move to
   Account".
3. Choose the target Account (e.g. an Advance/Deposit account), the
   Journal to post through, the Amount to move (defaults to the full
   residual, but can be reduced), and an optional Label/Date.
4. On Apply, the module:
   - creates ONE balanced journal entry for exactly the amount you
     entered (Debit/Credit the selected line's account <-> the target
     account, matching the sign of the residual),
   - posts it,
   - reconciles ONLY the new counterpart line against the line(s) you
     selected.

Because this uses Odoo's standard ``account.move.line.reconcile()``
method on exactly the lines involved, any amount not covered by your
entered "Amount" is left with its normal open residual automatically -
no custom "force close" or "force open" logic is used, so normal
Odoo accounting integrity (partner ledger, aged balance, tax reports,
bank reconciliation) is unaffected for any other transaction.

Nothing about the native Write-Off dialog, Reconciliation Models
(Internal Transfers / Bank Fees / Cash Discount), or Allow Partials
checkbox is modified. This module only adds a new, separate, opt-in
action.

Making the advance show up on the NEXT invoice
-----------------------------------------------
Odoo's native "Outstanding Credits" banner only scans accounts of
type Receivable/Payable. An account such as "Advance From Members"
is usually a Bank/Cash or plain Asset account, so it is never picked
up by that native banner - no configuration change to the account's
type is required or made by this module.

Instead, this module adds:

1. A new, OFF-by-default checkbox "Used for Customer/Vendor Advances"
   on the Chart of Accounts form. Tick it only on the account(s) you
   use to hold advances (e.g. 203001). Leaving it unticked (the
   default, on every account) changes nothing.
2. A banner on the Customer Invoice / Vendor Bill form: whenever the
   partner has an open balance on a flagged advance account, a blue
   banner appears with an "Apply Advance" button - the same
   experience as the native Outstanding Credits banner, just reading
   from your advance account(s) instead of Accounts
   Receivable/Payable.
3. Clicking "Apply Advance" posts one balanced bridging journal
   entry (Debit advance account / Credit the invoice's receivable
   or payable line) and reconciles both sides using Odoo's standard
   reconcile() method - this settles the invoice (fully or
   partially) and reduces the advance account balance accordingly.

No existing account, journal entry, or reconciliation elsewhere in
the system is read or modified by this feature; it only acts on the
specific invoice/bill you open and its own flagged advance lines.
""",
    "author": "Custom Development",
    "license": "LGPL-3",
    "depends": ["account_accountant"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/partial_move_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
