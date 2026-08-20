from odoo import models, fields, api
from odoo.exceptions import UserError


class PartialMoveWizard(models.TransientModel):
    _name = "partial.move.wizard"
    _description = "Move part of a residual balance to another account"

    line_ids = fields.Many2many(
        "account.move.line",
        string="Selected Journal Items",
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Partner", readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", readonly=True
    )
    total_residual = fields.Monetary(
        string="Total Residual",
        currency_field="currency_id",
        readonly=True,
        help="Positive = net debit balance on the source account "
        "(e.g. a receivable still owed by the customer). "
        "Negative = net credit balance (e.g. an overpayment / "
        "amount owed back to the customer).",
    )
    amount = fields.Monetary(
        string="Amount to Move",
        currency_field="currency_id",
        required=True,
        help="Portion of the residual to move to the target account. "
        "Any remaining amount stays open on the original account "
        "for future reconciliation, exactly as a normal partial "
        "payment would behave.",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Target Account",
        required=True,
        help="Account that will receive the moved amount "
        "(e.g. a customer advance / deposit account).",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ('general', 'bank', 'cash'))]",
    )
    label = fields.Char(string="Label", default="Partial move")
    date = fields.Date(
        string="Date", default=fields.Date.context_today
    )

    # ------------------------------------------------------------------
    # Shared validation: called from both default_get and action_apply so
    # the two can never drift apart on what they consider "safe".
    # ------------------------------------------------------------------
    def _check_selection(self, lines):
        if not lines:
            raise UserError("No journal items selected.")
        if len(lines.mapped("partner_id")) > 1:
            raise UserError(
                "Please select journal items belonging to a single "
                "partner only."
            )
        if len(lines.mapped("account_id")) > 1:
            raise UserError(
                "Please select journal items on a single account only "
                "(e.g. only Accounts Receivable lines)."
            )
        if len(lines.mapped("currency_id")) > 1:
            raise UserError(
                "Please select journal items in a single currency only."
            )
        if not lines.mapped("account_id").reconcile:
            raise UserError(
                "The selected account is not set up to allow "
                "reconciliation. Enable 'Allow Reconciliation' on this "
                "account first (Accounting > Configuration > Chart of "
                "Accounts)."
            )

        payments = lines.mapped("payment_id")
        if any(line.reconciled for line in lines) and not (
            len(payments) == 1
            and all(line.payment_id == payments for line in lines)
        ):
            raise UserError(
                "One or more selected journal items are already fully "
                "reconciled. Select only journal items from one payment "
                "to split a reconciled payment."
            )

        if payments:
            if len(payments) != 1:
                raise UserError(
                    "Select journal items belonging to one payment only."
                )
            # A payment already matched to a bank statement line cannot be
            # safely reduced here: shrinking payment.amount would also
            # shrink the bank/cash leg, misstating actual cash received.
            if payments.move_id.line_ids.mapped("statement_line_id"):
                raise UserError(
                    "This payment is already reconciled with a bank "
                    "statement line. Reducing it here would misstate the "
                    "recorded bank movement. Undo the bank reconciliation "
                    "first, or move the balance from a plain invoice line "
                    "instead."
                )

        return payments

    def _compute_residual(self, lines, payments):
        residual = sum(lines.mapped("amount_residual"))
        if not residual and payments and all(line.reconciled for line in lines):
            # A fully reconciled payment has no open amount_residual, but
            # its original move balance is still the amount that may be
            # split out. A customer payment posts Debit Bank / Credit AR,
            # so the AR line's `balance` is negative even though it should
            # be treated the same as a positive (debit-style) outstanding
            # amount for the purposes of this wizard. Negate it so the
            # sign convention matches amount_residual on an open invoice.
            residual = -sum(lines.mapped("balance"))
        return residual

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line_ids = self.env.context.get("active_ids")
        if not line_ids or self.env.context.get("active_model") != "account.move.line":
            return res

        lines = self.env["account.move.line"].browse(line_ids)
        payments = self._check_selection(lines)

        account = lines.account_id
        partner = lines.partner_id
        currency = lines[0].currency_id or lines[0].company_currency_id
        total_residual = self._compute_residual(lines, payments)

        res.update(
            {
                "line_ids": [(6, 0, lines.ids)],
                "partner_id": partner.id,
                "currency_id": currency.id,
                "total_residual": total_residual,
                "amount": abs(total_residual),
            }
        )
        return res

    def action_apply(self):
        self.ensure_one()
        lines = self.line_ids
        payments = self._check_selection(lines)

        # Re-read the selected account from the lines.  The action can be
        # opened and left on screen while another user reconciles a line.
        # Never create an entry against a different account in that case.
        source_account = lines.account_id
        if len(source_account) != 1:
            raise UserError(
                "The selected journal items must belong to a single account."
            )
        if self.account_id == source_account:
            raise UserError(
                "The target account must be different from the selected "
                "journal items' account."
            )

        residual = self._compute_residual(lines, payments)
        if residual == 0:
            raise UserError("The selected journal items have no open balance.")

        rounding = lines[0].company_currency_id.rounding or 0.01
        requested = abs(self.amount)
        if requested <= 0:
            raise UserError("The amount to move must be greater than zero.")
        if requested > abs(residual) + rounding:
            raise UserError(
                "The amount to move cannot exceed the total open "
                "residual (%.2f)." % abs(residual)
            )

        if payments:
            if not all(line.payment_id == payments for line in lines):
                raise UserError(
                    "To reduce a payment, select only its journal items."
                )
            if payments.currency_id != self.currency_id:
                raise UserError(
                    "The payment currency must match the selected journal "
                    "items' currency."
                )
            if requested > payments.amount + rounding:
                raise UserError(
                    "The amount to move cannot exceed the original payment "
                    "amount (%.2f)." % payments.amount
                )

        # --- Sign convention -------------------------------------------------
        # residual > 0 : source account carries a net DEBIT balance
        #                (e.g. an outstanding receivable).
        #                -> to reduce it: CREDIT the source account,
        #                   DEBIT the target account.
        # residual < 0 : source account carries a net CREDIT balance
        #                (e.g. a customer overpayment sitting on AR).
        #                -> to reduce it: DEBIT the source account,
        #                   CREDIT the target account.
        # This is derived from the actual residual every time - it must
        # never be hardcoded to a fixed account/direction, or the entry
        # will double the open balance instead of closing it.
        sign = 1 if residual > 0 else -1
        is_foreign = self.currency_id != self.env.company.currency_id

        def line_vals(account, debit_side):
            vals = {
                "account_id": account.id,
                "partner_id": self.partner_id.id,
                "name": self.label or "Partial move",
                "debit": requested if debit_side else 0.0,
                "credit": 0.0 if debit_side else requested,
            }
            if is_foreign:
                vals.update(
                    currency_id=self.currency_id.id,
                    amount_currency=requested if debit_side else -requested,
                )
            return vals

        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": self.date,
                "ref": (self.label or "Partial move") + " - booked to advance",
                "line_ids": [
                    # target: debited when sign > 0, credited when sign < 0
                    (0, 0, line_vals(source_account, debit_side=(sign > 0))),
                    # source: opposite side of target, closes the residual
                    (0, 0, line_vals(self.account_id, debit_side=(sign < 0))),
                ],
            }
        )
        move.action_post()



        # --- If the source was a payment, also shrink the payment itself ---
        # Safe here because _check_selection already blocked payments that
        # are reconciled against a bank statement line. This changes the
        # AR/AP-facing "applied" amount only; the payment's own bank/cash
        # leg amount is recomputed from the same reduced total, so make
        # sure that is the intended behavior for your accounting policy
        # before relying on this in a locked period.
        if payments:
            payment = payments

            if (
                self.env.company.fiscalyear_lock_date
                and payment.date
                and payment.date <= self.env.company.fiscalyear_lock_date
            ):
                raise UserError(
                    "This payment falls within a locked fiscal period and "
                    "cannot be modified."
                )

            payment_source_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id == source_account
            )
            original_counterparts = (
                payment_source_lines.matched_debit_ids.debit_move_id
                | payment_source_lines.matched_credit_ids.credit_move_id
            ) - payment_source_lines

            # Remove and reapply only the payment's invoice reconciliation.
            payment_source_lines.remove_move_reconcile()
            payment.action_draft()
            payment.write({"amount": payment.amount - requested})
            payment.move_id.action_post()
            payment.action_post()

            if original_counterparts:
                new_payment_source_lines = payment.move_id.line_ids.filtered(
                    lambda line: line.account_id == source_account
                )
                (new_payment_source_lines + original_counterparts).reconcile()