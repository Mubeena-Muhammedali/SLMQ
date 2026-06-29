/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

// ── KPI Card ─────────────────────────────────────────────────────────────────
class KpiCard extends Component {
    static template = "orchid_garage_dashboard.KpiCard";
    static props = {
        label: String,
        value: [String, Number],
        sub: { type: String, optional: true },
        icon: String,
        color: String,
        onClick: { type: Function, optional: true },
        loading: { type: Boolean, optional: true },
    };
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
class GarageDashboard extends Component {
    static template = "orchid_garage_dashboard.Dashboard";
    static components = { KpiCard };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            data: {
                pending_job_count: 0,
                closed_job_count: 0,
                closed_amount_total: 0,
                invoice_pending_count: 0,
                invoice_pending_amount_total: 0,
                est_draft_count: 0,
                est_confirmed_count: 0,
                est_completed_count: 0,
                est_confirmed_amount: 0,
                est_completed_amount: 0,
                inv_posted_count: 0,
                inv_posted_amount: 0,
                inv_paid_count: 0,
                inv_paid_amount: 0,
                inv_overdue_count: 0,
                inv_overdue_amount: 0,
            },
        });

        onWillStart(async () => { await this._loadData(); });
    }

    async _loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("garage.dashboard", "get_dashboard_data", []);
        } catch (e) {
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    // ── Formatters ────────────────────────────────────────────────────────────
    fmt(value) {
        return (value !== undefined && value !== null) ? String(value) : "—";
    }

    fmtMoney(value) {
        const symbol = this.state.data.currency_symbol || "";
        return `${symbol} ${new Intl.NumberFormat().format(value || 0)}`;
    }

    // ── Job Order actions ─────────────────────────────────────────────────────
    async openPendingJobs() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Jobs",
            res_model: "sale.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["od_job_status", "in", ["in_progress", "draft"]]],
        });
    }

    async openClosedJobs() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Closed Jobs",
            res_model: "sale.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["od_job_status", "=", "closed"]],
        });
    }

    async openInvoicePending() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Invoice Pending",
            res_model: "sale.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["od_job_status", "=", "closed"], ["invoice_status", "=", "to invoice"]],
        });
    }

    // ── Estimation actions ────────────────────────────────────────────────────
    async openEstDraft() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Draft Estimations",
            res_model: "garage.estimation",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "draft"]],
        });
    }

    async openEstConfirmed() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Confirmed Estimations",
            res_model: "garage.estimation",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "confirmed"]],
        });
    }

    async openEstCompleted() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Completed Estimations",
            res_model: "garage.estimation",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "completed"]],
        });
    }

    // ── Invoice actions ───────────────────────────────────────────────────────
    async openInvPosted() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Open Invoices",
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["move_type", "=", "out_invoice"], ["state", "=", "posted"],
                     ["payment_state", "not in", ["paid", "in_payment"]]],
        });
    }

    async openInvPaid() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paid Invoices",
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["move_type", "=", "out_invoice"], ["payment_state", "in", ["paid", "in_payment"]]],
        });
    }

    async openInvOverdue() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Overdue Invoices",
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["payment_state", "not in", ["paid", "in_payment"]],
                ["invoice_date_due", "<", new Date().toISOString().split("T")[0]],
            ],
        });
    }

    async refresh() { await this._loadData(); }
}

registry.category("actions").add("orchid_garage_dashboard", GarageDashboard);