import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class OdDeferredRevenueReport extends Component {
    static template = "orchid_deferred_revenue.OdDeferredRevenueReport";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        const today = new Date();
        const defaultPeriod = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
        this.state = useState({
            period: defaultPeriod,
            partner_id: "",
            partnerSearch: "",
            showPartnerDropdown: false,
            contract_id: "",
            contractSearch: "",
            showContractDropdown: false,
            journal_id: "",
            group_by_account: true,
            period_label: "",
            rows: [],
            totals: {},
            partners: [],
            contracts: [],
            journals: [],
            unfolded: {},
            details: {},
            loading: {},
            loadingPage: true,
            showFilters: false,
        });
        onWillStart(() => this.loadReport());
    }

    payload() {
        return {
            period: this.state.period,
            partner_id: this.state.partner_id || null,
            contract_id: this.state.contract_id || null,
            journal_id: this.state.journal_id || null,
            group_by_account: this.state.group_by_account,
            only_active: true,
        };
    }

    _fmt(value) {
        const number = Number(value || 0);
        if (!number) {
            return "0.00";
        }
        return number.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async loadReport() {
        this.state.loadingPage = true;
        try {
            const res = await this.orm.call("od.deferred.revenue.report", "get_report", [this.payload()]);
            this.state.period_label = res.period.label;
            this.state.rows = res.rows || [];
            this.state.totals = res.totals || {};
            this.state.partners = res.filters?.partners || [];
            this.state.contracts = res.filters?.contracts || [];
            this.state.journals = res.filters?.journals || [];
            this.state.unfolded = {};
            this.state.details = {};
            this.state.loading = {};
        } catch (error) {
            console.error("Deferred Revenue report failed:", error);
            const detail = error?.data?.message || error?.message || "";
            this.notification.add(
                detail ? `${_t("Failed to load deferred revenue report.")} ${detail}` : _t("Failed to load deferred revenue report."),
                {
                    title: _t("Deferred Revenue"),
                    type: "danger",
                    sticky: true,
                }
            );
        } finally {
            this.state.loadingPage = false;
        }
    }

    async onReload() {
        await this.loadReport();
    }

    onToggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    async onPeriodShift(delta) {
        const [year, month] = this.state.period.split("-").map(Number);
        const d = new Date(year, month - 1 + delta, 1);
        this.state.period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
        await this.loadReport();
    }

    async onPeriodChange(ev) {
        const val = ev.currentTarget.value;
        if (val) {
            this.state.period = val.slice(0, 7);
            await this.loadReport();
        }
    }

    filteredPartners() {
        const q = (this.state.partnerSearch || "").trim().toLowerCase();
        if (!q) {
            return this.state.partners;
        }
        return this.state.partners.filter((p) => (p.name || "").toLowerCase().includes(q));
    }

    onPartnerFocus() {
        this.state.showPartnerDropdown = true;
    }

    onPartnerSearchInput(ev) {
        this.state.partnerSearch = ev.currentTarget.value || "";
        this.state.showPartnerDropdown = true;
    }

    onPartnerBlur() {
        // small delay so the mousedown on an option fires before we close the dropdown
        setTimeout(() => {
            this.state.showPartnerDropdown = false;
        }, 150);
    }

    async onPartnerSelect(partner) {
        this.state.partner_id = partner ? String(partner.id) : "";
        this.state.partnerSearch = partner ? partner.name : "";
        this.state.showPartnerDropdown = false;
        await this.loadReport();
    }

    async onJournalChange(ev) {
        this.state.journal_id = ev.currentTarget.value || "";
        await this.loadReport();
    }

    filteredContracts() {
        const q = (this.state.contractSearch || "").trim().toLowerCase();
        if (!q) {
            return this.state.contracts;
        }
        return this.state.contracts.filter((c) => (c.name || "").toLowerCase().includes(q));
    }

    onContractFocus() {
        this.state.showContractDropdown = true;
    }

    onContractSearchInput(ev) {
        this.state.contractSearch = ev.currentTarget.value || "";
        this.state.showContractDropdown = true;
    }

    onContractBlur() {
        // small delay so the mousedown on an option fires before we close the dropdown
        setTimeout(() => {
            this.state.showContractDropdown = false;
        }, 150);
    }

    async onContractSelect(contract) {
        this.state.contract_id = contract ? String(contract.id) : "";
        this.state.contractSearch = contract ? contract.name : "";
        this.state.showContractDropdown = false;
        await this.loadReport();
    }

    async onToggleGroupByAccount() {
        this.state.group_by_account = !this.state.group_by_account;
        await this.loadReport();
    }

    async onToggle(row, bucket) {
        const key = `${row.account_id}|${bucket}`;
        if (this.state.unfolded[key]) {
            this.state.unfolded[key] = false;
            return;
        }
        this.state.unfolded[key] = true;
        if (this.state.details[key]) {
            return;
        }
        this.state.loading[key] = true;
        try {
            const res = await this.orm.call("od.deferred.revenue.report", "get_row_lines", [
                row.account_id,
                bucket,
                this.payload(),
            ]);
            this.state.details[key] = res.lines || [];
        } catch (error) {
            console.error("Deferred Revenue drilldown failed:", error);
            this.notification.add(_t("Failed to load drilldown lines."), {
                title: _t("Deferred Revenue"),
                type: "danger",
            });
        } finally {
            this.state.loading[key] = false;
        }
    }

    async onOpenContracts(row, bucket) {
        const action = await this.orm.call("od.deferred.revenue.report", "open_contracts", [
            row.account_id,
            bucket,
            this.payload(),
        ]);
        return this.actionService.doAction(action);
    }

    async onExportXlsx() {
        const res = await this.orm.call("od.deferred.revenue.report", "export_xlsx", [this.payload()]);
        if (res?.url) {
            window.open(res.url, "_blank");
        }
    }

    async onExportPdf() {
        const action = await this.orm.call("od.deferred.revenue.report", "export_pdf", [this.payload()]);
        return this.actionService.doAction(action);
    }
}

registry.category("actions").add("od_deferred_revenue_report_action", OdDeferredRevenueReport);
