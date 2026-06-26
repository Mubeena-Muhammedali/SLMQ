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
            // orm.create returns a plain integer (the new record's id) in Odoo 16–19.
            // Pass a plain object (not an array) for a single record.
            const id = await this.orm.create("garage.dashboard", {});

            // orm.read expects an array of ids.
            const records = await this.orm.read(
                "garage.dashboard",
                [id],
                [
                    "pending_job_count",
                    "closed_job_count",
                    "closed_amount_total",
                    "invoice_pending_count",
                    "invoice_pending_amount_total",
                    "closed_this_month",
                    "invoiced_this_month",
                ]
            );
            if (records && records.length) {
                Object.assign(this.state.data, records[0]);
            }
        } catch (e) {
            console.error("GarageDashboard._loadData failed:", e);
        } finally {
            this.state.loading = false;
        }
    }

    // ── Formatters ─────────────────────────────────────────────────────────────

    fmt(value) {
        return (value !== undefined && value !== null) ? String(value) : "—";
    }

    fmtMoney(value) {
        if (value === undefined || value === null) return "—";
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
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
