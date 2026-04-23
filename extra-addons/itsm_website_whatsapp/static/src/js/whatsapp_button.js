/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ItsmWhatsAppFloat = publicWidget.Widget.extend({
    selector: "#itsm_wa_float",
    events: {
        "click .itsm-wa-btn": "_onClickButton",
        "click .itsm-wa-tooltip-close": "_onCloseTooltip",
    },

    start() {
        this._super(...arguments);
        this._readConfig();
        this._applyColor();

        if (this._shouldShow()) {
            this.el.style.display = "";
        } else {
            this.el.style.display = "none";
        }
    },

    // ---- Private ----

    _readConfig() {
        const ds = this.el.dataset;
        this._phone = (ds.phone || "").replace(/[^+\d]/g, "");
        this._message = ds.message || "";
        this._color = ds.color || "#25D366";
        this._pulse = ds.pulse === "1";
        this._businessHours = ds.businessHours === "1";
        this._hourFrom = parseFloat(ds.hourFrom) || 8;
        this._hourTo = parseFloat(ds.hourTo) || 18;
        this._days = (ds.days || "1,2,3,4,5")
            .split(",")
            .map((d) => parseInt(d.trim(), 10))
            .filter((d) => !isNaN(d));
    },

    _applyColor() {
        const btn = this.el.querySelector(".itsm-wa-btn");
        if (btn) {
            btn.style.backgroundColor = this._color;
        }
        const pulse = this.el.querySelector(".itsm-wa-pulse");
        if (pulse) {
            pulse.style.backgroundColor = this._color;
        }
    },

    _shouldShow() {
        if (!this._phone) {
            return false;
        }
        if (!this._businessHours) {
            return true;
        }
        const now = new Date();
        // JS getDay: 0=Sunday, convert to 1=Monday..7=Sunday
        let jsDay = now.getDay();
        let isoDay = jsDay === 0 ? 7 : jsDay;

        if (!this._days.includes(isoDay)) {
            return false;
        }
        const currentHour = now.getHours() + now.getMinutes() / 60;
        return currentHour >= this._hourFrom && currentHour < this._hourTo;
    },

    _buildUrl() {
        // Use wa.me for universal support (mobile app + web)
        let url = "https://wa.me/" + this._phone.replace("+", "");
        if (this._message) {
            url += "?text=" + encodeURIComponent(this._message);
        }
        return url;
    },

    // ---- Handlers ----

    _onClickButton(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const url = this._buildUrl();
        window.open(url, "_blank", "noopener,noreferrer");
    },

    _onCloseTooltip(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const tooltip = this.el.querySelector(".itsm-wa-tooltip");
        if (tooltip) {
            tooltip.style.display = "none";
        }
    },
});

export default publicWidget.registry.ItsmWhatsAppFloat;
