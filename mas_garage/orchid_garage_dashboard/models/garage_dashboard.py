from odoo import api, models


class GarageDashboard(models.AbstractModel):
    _name = "garage.dashboard"

    @api.model
    def get_dashboard_data(self):
        SaleOrder = self.env["sale.order"]
        Estimation = self.env["garage.estimation"]
        Invoice = self.env["account.move"]

        # ── Job Orders ────────────────────────────────────────────────────────
        pending = SaleOrder.search([
            ("od_job_status", "in", ["draft", "in_progress"])
        ])
        closed = SaleOrder.search([
            ("od_job_status", "=", "closed")
        ])
        invoice_pending = SaleOrder.search([
            ("od_job_status", "=", "closed"),
            ("invoice_status", "=", "to invoice"),
        ])

        # ── Estimations ───────────────────────────────────────────────────────
        est_draft = Estimation.search([("state", "=", "draft")])
        est_confirmed = Estimation.search([("state", "=", "confirmed")])
        est_completed = Estimation.search([("state", "=", "completed")])

        # ── Invoices (customer invoices only) ─────────────────────────────────
        inv_posted = Invoice.search([
            ("move_type", "=", "out_invoice"),
            ("payment_state", "not in", ["paid", "in_payment"]),
            ("state", "=", "posted"),
        ])
        inv_paid = Invoice.search([
            ("move_type", "=", "out_invoice"),
            ("payment_state", "in", ["paid", "in_payment"]),
        ])
        inv_overdue = Invoice.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "not in", ["paid", "in_payment"]),
            ("invoice_date_due", "<", fields_date()),
        ])

        return {
            # jobs
            "pending_job_count": len(pending),
            "closed_job_count": len(closed),
            "closed_amount_total": sum(closed.mapped("amount_total")),
            "invoice_pending_count": len(invoice_pending),
            "invoice_pending_amount_total": sum(invoice_pending.mapped("amount_to_invoice")),
            # estimations
            "est_draft_count": len(est_draft),
            "est_confirmed_count": len(est_confirmed),
            "est_completed_count": len(est_completed),
            "est_confirmed_amount": sum(est_confirmed.mapped("amount_total")),
            "est_completed_amount": sum(est_completed.mapped("amount_total")),
            # invoices
            "inv_posted_count": len(inv_posted),
            "inv_posted_amount": sum(inv_posted.mapped("amount_residual")),
            "inv_paid_count": len(inv_paid),
            "inv_paid_amount": sum(inv_paid.mapped("amount_total")),
            "inv_overdue_count": len(inv_overdue),
            "inv_overdue_amount": sum(inv_overdue.mapped("amount_residual")),
            # misc
            "currency_symbol": self.env.company.currency_id.symbol,
        }


def fields_date():
    from datetime import date
    return date.today().isoformat()