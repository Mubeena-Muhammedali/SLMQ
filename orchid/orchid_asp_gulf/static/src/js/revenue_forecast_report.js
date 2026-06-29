odoo.define("orchid_asp_gulf.revenue_forecast_report", function (require) {
    "use strict";

    var AbstractAction = require("web.AbstractAction");
    var core = require("web.core");
    var session = require("web.session");

    var QWeb = core.qweb;
    var _t = core._t;

    var RevenueForecastReport = AbstractAction.extend({
        template: "orchid_asp_gulf.RevenueForecastReport",
        events: {
            "click .o_rfr_reload": "_onReload",
            "click .o_rfr_export": "_onExport",
            "input .o_rfr_search": "_onSearch",
            "change .o_rfr_start": "_onDateChange",
            "change .o_rfr_end": "_onDateChange",
            "change .o_rfr_partner": "_onPartnerChange",
            "change .o_rfr_contract": "_onContractChange",
            "change .o_rfr_category": "_onCategoryChange",
            "change .o_rfr_rev_type": "_onRevTypeChange",
            "change .o_rfr_rows": "_onRowsChange",
            "click .o_rfr_prev": "_onPrev",
            "click .o_rfr_next": "_onNext",
            "click .o_rfr_toggle": "_onToggle",
            "click .o_rfr_open_contracts": "_onOpenContracts",
        },

        init: function () {
            this._super.apply(this, arguments);
            this.state = {
                start_date: "2026-07-01",
                end_date: "2027-06-30",
                partner_id: "",
                contract_id: "",
                category_id: "",
                rev_type: "",
                search: "",
                months: [],
                summary: [],
                partners: [],
                contracts: [],
                categories: [],
                rev_types: [],
                totals: {},
                grand_total: 0,
                unfolded: {},
                details: {},
                loading: {},
                pager: {
                    total: 0,
                    page: 1,
                    page_size: 50,
                    pages: 1,
                    from: 0,
                    to: 0,
                },
            };
            this._filtered = [];
        },

        willStart: function () {
            return Promise.all([this._super.apply(this, arguments), this._loadSummary()]);
        },

        start: function () {
            this._render();
            return this._super.apply(this, arguments);
        },

        _payload: function () {
            return {
                start_date: this.state.start_date,
                end_date: this.state.end_date,
                partner_id: this.state.partner_id || null,
                contract_id: this.state.contract_id || null,
                category_id: this.state.category_id || null,
                rev_type: this.state.rev_type || null,
                search_text: this.state.search || null,
                only_active: true,
            };
        },

        _fmt: function (value) {
            var number = Number(value || 0);
            if (!number) {
                return "-";
            }
            return number.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            });
        },

        _loadSummary: function () {
            var self = this;
            return this._rpc({
                model: "od.revenue.forecast.report",
                method: "view_report",
                args: [this._payload()],
            }).then(function (res) {
                self.state.months = res.months || [];
                self.state.summary = res.summary || [];
                self.state.partners = res.partners || [];
                self.state.contracts = res.contracts || [];
                self.state.categories = res.categories || [];
                self.state.rev_types = res.rev_types || [];
                self.state.totals = res.totals || {};
                self.state.grand_total = res.grand_total || 0;
                self.state.unfolded = {};
                self.state.details = {};
                self.state.loading = {};
                self.state.pager.page = 1;
                self._applyFilters();
            });
        },

        _applyFilters: function () {
            var rows = this.state.summary || [];
            this._filtered = rows;

            var pageSize = Number(this.state.pager.page_size || 50);
            var total = rows.length;
            var pages = Math.max(1, Math.ceil(total / pageSize));
            var page = Math.min(Math.max(1, Number(this.state.pager.page || 1)), pages);
            var start = (page - 1) * pageSize;
            var end = Math.min(start + pageSize, total);

            this.state.pager.total = total;
            this.state.pager.pages = pages;
            this.state.pager.page = page;
            this.state.pager.from = total ? start + 1 : 0;
            this.state.pager.to = end;
            this.state.visibleRows = rows.slice(start, end);
        },

        _render: function () {
            this._applyFilters();
            this.$el.html(QWeb.render("orchid_asp_gulf.RevenueForecastReportContent", {
                widget: this,
                state: this.state,
                rows: this.state.visibleRows || [],
            }));
        },

        _onReload: function () {
            var self = this;
            this._loadSummary().then(function () {
                self._render();
            });
        },

        _onExport: function () {
            return this._rpc({
                model: "od.revenue.forecast.report",
                method: "export_xlsx",
                args: [this._payload()],
            }).then(function (res) {
                if (res && res.url) {
                    window.open(res.url, "_blank");
                }
            });
        },

        _onSearch: function (ev) {
            var self = this;
            this.state.search = ev.currentTarget.value || "";
            this.state.pager.page = 1;
            clearTimeout(this._searchTimer);
            this._searchTimer = setTimeout(function () {
                self._onReload();
            }, 350);
        },

        _onDateChange: function () {
            this.state.start_date = this.$(".o_rfr_start").val() || "2026-07-01";
            this.state.end_date = this.$(".o_rfr_end").val() || "2027-06-30";
            this._onReload();
        },

        _onRevTypeChange: function (ev) {
            this.state.rev_type = ev.currentTarget.value || "";
            this._onReload();
        },

        _onCategoryChange: function (ev) {
            this.state.category_id = ev.currentTarget.value || "";
            this._onReload();
        },

        _onPartnerChange: function (ev) {
            this.state.partner_id = ev.currentTarget.value || "";
            this.state.contract_id = "";
            this._onReload();
        },

        _onContractChange: function (ev) {
            this.state.contract_id = ev.currentTarget.value || "";
            this._onReload();
        },

        _onRowsChange: function (ev) {
            this.state.pager.page_size = parseInt(ev.currentTarget.value, 10) || 50;
            this.state.pager.page = 1;
            this._render();
        },

        _onPrev: function () {
            if (this.state.pager.page > 1) {
                this.state.pager.page -= 1;
                this._render();
            }
        },

        _onNext: function () {
            if (this.state.pager.page < this.state.pager.pages) {
                this.state.pager.page += 1;
                this._render();
            }
        },

        _onToggle: function (ev) {
            var self = this;
            var key = $(ev.currentTarget).data("key");
            if (this.state.unfolded[key]) {
                this.state.unfolded[key] = false;
                this._render();
                return;
            }
            this.state.unfolded[key] = true;
            if (this.state.details[key]) {
                this._render();
                return;
            }
            this.state.loading[key] = true;
            this._render();
            return this._rpc({
                model: "od.revenue.forecast.report",
                method: "get_row_lines",
                args: [key, this._payload()],
            }).then(function (res) {
                self.state.details[key] = res.lines || [];
            }).guardedCatch(function () {
                self.do_warn(_t("Revenue Forecast"), _t("Failed to load drilldown lines."));
            }).finally(function () {
                self.state.loading[key] = false;
                self._render();
            });
        },

        _onOpenContracts: function (ev) {
            var key = $(ev.currentTarget).data("key");
            var self = this;
            return this._rpc({
                model: "od.revenue.forecast.report",
                method: "open_contracts",
                args: [key, this._payload()],
            }).then(function (action) {
                return self.do_action(action);
            });
        },
    });

    core.action_registry.add("od_revenue_forecast_report_action", RevenueForecastReport);
    return RevenueForecastReport;
});
