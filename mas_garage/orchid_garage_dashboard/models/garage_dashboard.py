from odoo import api, fields, models
from datetime import date, timedelta


class GarageDashboard(models.TransientModel):
    """
    Transient model that provides computed KPIs for the Garage Dashboard.
    All data is read from sale.order (which acts as the Job / Work Order).

    Job Status field on sale.order (od_job_status):
        draft       → Quotation / not yet started
        in_progress → Job is running
        closed      → Job is finished

    "Pending Jobs" = sale orders whose od_job_status in ('in_progress', 'draft').

    "Closed Jobs" = sale orders with od_job_status == 'closed'.

    "Invoice Pending Jobs" = sale orders with od_job_status == 'closed'
                             AND invoice_status == 'to invoice'.
    """
    _name = 'garage.dashboard'
    _description = 'Garage Dashboard'

    # ── summary counts ─────────────────────────────────────────────────────────

    pending_job_count = fields.Integer(compute='_compute_all')
    closed_job_count = fields.Integer(compute='_compute_all')
    invoice_pending_count = fields.Integer(compute='_compute_all')

    # totals for closed / invoice-pending amounts
    closed_amount_total = fields.Float(compute='_compute_all', digits=(16, 2))
    invoice_pending_amount_total = fields.Float(compute='_compute_all', digits=(16, 2))

    # ── this month KPIs ────────────────────────────────────────────────────────

    closed_this_month = fields.Integer(compute='_compute_all')
    invoiced_this_month = fields.Float(compute='_compute_all', digits=(16, 2))

    @api.depends()
    def _compute_all(self):
        SaleOrder = self.env['sale.order']
        today = date.today()
        month_start = today.replace(day=1)

        for rec in self:
            # ── Pending Jobs ──────────────────────────────────────────────────
            # FIX: was ('od_job_status', '=', ('in_progress','draft')) — wrong operator
            pending = SaleOrder.search([
                ('od_job_status', 'in', ('in_progress', 'draft')),
            ])
            rec.pending_job_count = len(pending)

            # ── Closed Jobs ───────────────────────────────────────────────────
            closed = SaleOrder.search([('od_job_status', '=', 'closed')])
            rec.closed_job_count = len(closed)
            rec.closed_amount_total = sum(closed.mapped('amount_total'))

            closed_month = SaleOrder.search([
                ('od_job_status', '=', 'closed'),
                ('date_order', '>=', fields.Date.to_string(month_start)),
            ])
            rec.closed_this_month = len(closed_month)

            # ── Invoice Pending ───────────────────────────────────────────────
            # FIX: was ('invoice_status', '==', 'to invoice') — double == is invalid
            inv_pending = SaleOrder.search([
                ('od_job_status', '=', 'closed'),
                ('invoice_status', '=', 'to invoice'),
            ])
            rec.invoice_pending_count = len(inv_pending)
            rec.invoice_pending_amount_total = sum(inv_pending.mapped('amount_total'))

            # ── Invoiced This Month ───────────────────────────────────────────
            inv_month = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', fields.Date.to_string(month_start)),
            ])
            rec.invoiced_this_month = sum(inv_month.mapped('amount_total'))

    # ── action helpers ─────────────────────────────────────────────────────────

    def action_view_pending_jobs(self):
        # FIX: was ('od_job_status', '=', ('in_progress','draft')) — wrong operator
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Jobs',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('od_job_status', 'in', ['in_progress', 'draft']),
            ],
        }

    def action_view_closed_jobs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Closed Jobs',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('od_job_status', '=', 'closed')],
        }

    def action_view_invoice_pending(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Pending Jobs',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('od_job_status', '=', 'closed'),
                ('invoice_status', '=', 'to invoice'),
            ],
        }
