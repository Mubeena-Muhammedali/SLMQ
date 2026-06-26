from odoo import api, models

class GarageDashboard(models.AbstractModel):
    _name = "garage.dashboard"

    @api.model
    def get_dashboard_data(self):
        SaleOrder = self.env["sale.order"]

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

        return {
            "pending_job_count": len(pending),
            "closed_job_count": len(closed),
            "closed_amount_total": sum(closed.mapped("amount_total")),
            "invoice_pending_count": len(invoice_pending),
            "invoice_pending_amount_total": sum(invoice_pending.mapped("amount_to_invoice")),
            "currency_symbol": self.env.company.currency_id.symbol,
        }