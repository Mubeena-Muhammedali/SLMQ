/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

// ──────────────────────────────────────────────────────────────────────────────
// KPI Card Component
// ──────────────────────────────────────────────────────────────────────────────
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

// ──────────────────────────────────────────────────────────────────────────────
// Main Dashboard Component
// ──────────────────────────────────────────────────────────────────────────────
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
                closed_this_month: 0,
                invoiced_this_month: 0,
            },
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        this.state.loading = true;

        try {
            this.state.data = await this.orm.call(
                "garage.dashboard",
                "get_dashboard_data",
                []
            );

            console.log(this.state.data);
        } catch (e) {
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    // ── Formatters ─────────────────────────────────────────────────────────────

    fmt(value) {
        return (value !== undefined && value !== null) ? String(value) : "—";
    }

   fmtMoney(value) {
        const symbol = this.state.data.currency_symbol || "";
        return `${symbol} ${new Intl.NumberFormat().format(value || 0)}`;
    }

    // ── Click handlers ─────────────────────────────────────────────────────────

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
            domain: [
                ["od_job_status", "=", "closed"],
                ["invoice_status", "=", "to invoice"],
            ],
        });
    }

    async refresh() {
        await this._loadData();
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Register as a client action
// ──────────────────────────────────────────────────────────────────────────────
registry.category("actions").add("orchid_garage_dashboard", GarageDashboard);
