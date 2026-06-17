# -*- coding: utf-8 -*-
import base64
import io
from datetime import date, datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None


class OdRevenueForecastReport(models.TransientModel):
    _name = "od.revenue.forecast.report"
    _description = "Revenue Forecast Report"

    _FY_START = "2026-07-01"
    _FY_END = "2027-06-30"

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_rfr_monthly_line_service_period_idx
            ON od_contract_monthly_line (service_id, period_to)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_rfr_monthly_line_period_idx
            ON od_contract_monthly_line (period_to)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_rfr_contract_payment_partner_contract_idx
            ON od_contract_payment (partner_id, contract_id, billing_cycle)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_rfr_payment_line_service_period_idx
            ON od_contract_payment_line (service_id, period_to)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_rfr_contract_line_state_product_idx
            ON od_asp_contract_line (state, product_id, billing_cycle)
        """)

    def _normalize_payload(self, payload=None):
        payload = payload or {}
        return {
            "start_date": payload.get("start_date") or self._FY_START,
            "end_date": payload.get("end_date") or self._FY_END,
            "partner_id": payload.get("partner_id") or None,
            "contract_id": payload.get("contract_id") or None,
            "category_id": payload.get("category_id") or None,
            "rev_type": payload.get("rev_type") or None,
            "search_text": (payload.get("search_text") or "").strip(),
            "only_active": payload.get("only_active", True),
        }

    def _get_category_ids(self, category_id):
        if not category_id:
            return []
        return self.env["product.category"].search([("id", "child_of", int(category_id))]).ids

    def _months(self, start_date, end_date):
        start = fields.Date.from_string(start_date).replace(day=1)
        end = fields.Date.from_string(end_date).replace(day=1)
        months = []
        current = start
        while current <= end:
            months.append({
                "key": current.strftime("%Y-%m"),
                "label": current.strftime("%b-%y"),
            })
            year = current.year + (1 if current.month == 12 else 0)
            month = 1 if current.month == 12 else current.month + 1
            current = date(year, month, 1)
        return months

    def _base_where(self, payload, include_partner=True, include_contract=True, include_category=True):
        params = {
            "company_id": self.env.company.id,
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
        }
        where = [
            "cont.company_id = %(company_id)s",
            "ml.period_to >= %(start_date)s",
            "ml.period_to <= %(end_date)s",
        ]
        if payload["only_active"]:
            where.append("cont.state = 'active'")
            where.append("cont_line.state = 'active'")
        if include_partner and payload["partner_id"]:
            params["partner_id"] = int(payload["partner_id"])
            where.append("pay.partner_id = %(partner_id)s")
        if include_contract and payload["contract_id"]:
            params["contract_id"] = int(payload["contract_id"])
            where.append("cont.id = %(contract_id)s")
        if include_category and payload["category_id"]:
            category_ids = self._get_category_ids(payload["category_id"])
            if category_ids:
                params["category_ids"] = category_ids
                where.append("pt.categ_id = ANY(%(category_ids)s)")
        if payload["rev_type"]:
            params["rev_type"] = payload["rev_type"]
            rev_type_sql = self._rev_type_sql()
            where.append("""
                {rev_type_sql} = %(rev_type)s
            """.format(rev_type_sql=rev_type_sql))
        if payload["search_text"]:
            params["search_text"] = "%%%s%%" % payload["search_text"].lower()
            rev_type_sql = self._rev_type_sql()
            where.append("""
                (
                    lower(COALESCE(rp.name, '')) LIKE %(search_text)s
                    OR lower(COALESCE(cont.name, '')) LIKE %(search_text)s
                    OR lower(COALESCE(cont.contract_code, '')) LIKE %(search_text)s
                    OR lower(COALESCE(cont_line.name, '')) LIKE %(search_text)s
                    OR lower(COALESCE(pt.name, '')) LIKE %(search_text)s
                    OR lower(COALESCE(pc.name, '')) LIKE %(search_text)s
                    OR lower({rev_type_sql}) LIKE %(search_text)s
                )
            """.format(rev_type_sql=rev_type_sql))
        return where, params

    def _from_sql(self, payload=None, include_partner=True, include_contract=True):
        payload = payload or {}
        forecast_where = [
            "cont.state = 'active'",
            "cont_line.state = 'active'",
            "COALESCE(pay.billing_cycle, cont_line.billing_cycle, '') NOT IN ('one_time', 'annually')",
            "COALESCE(NULLIF(pay.per_month * COALESCE(cont.od_exchange_rate, 1.0), 0.0), last_ml.amount, 0.0) != 0",
        ]
        event_forecast_where = [
            "cont.state = 'active'",
            "cont_line.state = 'active'",
            "COALESCE(pay.billing_cycle, cont_line.billing_cycle, '') IN ('one_time', 'annually')",
            "COALESCE(NULLIF(pay.total_amount * COALESCE(cont.od_exchange_rate, 1.0), 0.0), NULLIF(pay.per_month * 12 * COALESCE(cont.od_exchange_rate, 1.0), 0.0), last_event.amount, 0.0) != 0",
        ]
        if include_partner and payload.get("partner_id"):
            forecast_where.append("pay.partner_id = %(partner_id)s")
            event_forecast_where.append("pay.partner_id = %(partner_id)s")
        if include_contract and payload.get("contract_id"):
            forecast_where.append("cont.id = %(contract_id)s")
            event_forecast_where.append("cont.id = %(contract_id)s")

        return """
            FROM (
                SELECT
                    ml.id::bigint AS id,
                    ml.service_id AS service_id,
                    ml.period_to AS period_to,
                    ml.amount AS amount,
                    FALSE AS is_forecast
                FROM od_contract_monthly_line ml
                JOIN od_contract_payment pay ON pay.id = ml.service_id
                LEFT JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
                WHERE COALESCE(pay.billing_cycle, cont_line.billing_cycle, '') NOT IN ('one_time', 'annually')

                UNION ALL

                SELECT
                    (
                        (pl.id::bigint * 10)
                        + 1
                    ) AS id,
                    pl.service_id AS service_id,
                    pl.period_to AS period_to,
                    pl.amount * COALESCE(cont.od_exchange_rate, 1.0) AS amount,
                    FALSE AS is_forecast
                FROM od_contract_payment_line pl
                JOIN od_contract_payment pay ON pay.id = pl.service_id
                JOIN od_asp_contract cont ON cont.id = pay.contract_id
                LEFT JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
                WHERE COALESCE(pay.billing_cycle, cont_line.billing_cycle, '') IN ('one_time', 'annually')

                UNION ALL

                SELECT
                    -(
                        (pay.id::bigint * 1000000)
                        + (EXTRACT(YEAR FROM gs)::bigint * 100)
                        + EXTRACT(MONTH FROM gs)::bigint
                    ) AS id,
                    pay.id AS service_id,
                    (
                        date_trunc('month', gs)::date
                        + interval '1 month'
                        - interval '1 day'
                    )::date AS period_to,
                    COALESCE(NULLIF(pay.per_month * COALESCE(cont.od_exchange_rate, 1.0), 0.0), last_ml.amount, 0.0) AS amount,
                    TRUE AS is_forecast
                FROM od_contract_payment pay
                JOIN od_asp_contract cont ON cont.id = pay.contract_id
                JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
                LEFT JOIN LATERAL (
                    SELECT MAX(line.period_to) AS max_period_to
                    FROM od_contract_monthly_line line
                    WHERE line.service_id = pay.id
                        AND line.period_to <= %(end_date)s
                ) last_period ON TRUE
                LEFT JOIN LATERAL (
                    SELECT amount
                    FROM od_contract_monthly_line line
                    WHERE line.service_id = pay.id
                    ORDER BY line.period_to DESC, line.id DESC
                    LIMIT 1
                ) last_ml ON TRUE
                JOIN LATERAL generate_series(
                    date_trunc(
                        'month',
                        GREATEST(
                            %(start_date)s::date,
                            COALESCE((last_period.max_period_to + interval '1 day')::date, pay.start_date, %(start_date)s::date)
                        )
                    )::date,
                    date_trunc('month', %(end_date)s::date)::date,
                    interval '1 month'
                ) gs ON TRUE
                WHERE {forecast_where}

                UNION ALL

                SELECT
                    -(
                        (pay.id::bigint * 1000000)
                        + (EXTRACT(YEAR FROM gs)::bigint * 100)
                        + EXTRACT(MONTH FROM gs)::bigint
                    ) AS id,
                    pay.id AS service_id,
                    gs::date AS period_to,
                    COALESCE(NULLIF(pay.total_amount * COALESCE(cont.od_exchange_rate, 1.0), 0.0), NULLIF(pay.per_month * 12 * COALESCE(cont.od_exchange_rate, 1.0), 0.0), last_event.amount, 0.0) AS amount,
                    TRUE AS is_forecast
                FROM od_contract_payment pay
                JOIN od_asp_contract cont ON cont.id = pay.contract_id
                JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
                LEFT JOIN LATERAL (
                    SELECT
                        MAX(pl.period_to) AS max_period_to,
                        (array_agg(pl.amount * COALESCE(cont.od_exchange_rate, 1.0) ORDER BY pl.period_to DESC, pl.id DESC))[1] AS amount
                    FROM od_contract_payment_line pl
                    WHERE pl.service_id = pay.id
                        AND pl.period_to <= %(end_date)s
                ) last_event ON TRUE
                JOIN LATERAL generate_series(
                    GREATEST(
                        %(start_date)s::date,
                        COALESCE((last_event.max_period_to + interval '1 year')::date, pay.end_date, pay.start_date, %(start_date)s::date)
                    ),
                    %(end_date)s::date,
                    interval '1 year'
                ) gs ON TRUE
                WHERE {event_forecast_where}
            ) ml
            JOIN od_contract_payment pay ON pay.id = ml.service_id
            JOIN od_asp_contract cont ON cont.id = pay.contract_id
            JOIN res_partner rp ON rp.id = pay.partner_id
            LEFT JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
            LEFT JOIN product_product pp ON pp.id = cont_line.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc ON pc.id = pt.categ_id
        """.format(
            forecast_where=" AND ".join(forecast_where),
            event_forecast_where=" AND ".join(event_forecast_where),
        )

    def _rev_type_sql(self):
        return """
            CASE pt.od_revenue_type
                WHEN 'hosting' THEN 'Hosting'
                WHEN 'public_cloud' THEN 'Public Cloud'
                WHEN 'm365' THEN 'M365'
                WHEN 'prof_serv' THEN 'Prof Serv'
                WHEN 'trading' THEN 'Trading'
                ELSE 'Not Set'
            END
        """

    def _filter_options(self, payload):
        rev_type_sql = self._rev_type_sql()

        partner_where, partner_params = self._base_where(payload, include_partner=False)
        self.env.cr.execute("""
            SELECT DISTINCT
                pay.partner_id AS id,
                rp.name AS name,
                lower(rp.name) AS sort_name
            {from_sql}
            WHERE {where_sql}
            ORDER BY sort_name
        """.format(
            from_sql=self._from_sql(payload, include_partner=False),
            where_sql=" AND ".join(partner_where),
            rev_type_sql=rev_type_sql,
        ), partner_params)
        partners = [{"id": r["id"], "name": r["name"] or ""} for r in self.env.cr.dictfetchall()]

        contract_where, contract_params = self._base_where(payload, include_contract=False)
        self.env.cr.execute("""
            SELECT DISTINCT
                cont.id AS id,
                COALESCE(cont.contract_code, cont.name, '') AS name,
                cont.name AS number,
                rp.name AS partner_name,
                lower(rp.name) AS partner_sort_name,
                lower(COALESCE(cont.contract_code, cont.name, '')) AS contract_sort_name
            {from_sql}
            WHERE {where_sql}
            ORDER BY partner_sort_name, contract_sort_name
        """.format(
            from_sql=self._from_sql(payload, include_contract=False),
            where_sql=" AND ".join(contract_where),
            rev_type_sql=rev_type_sql,
        ), contract_params)
        contracts = []
        for row in self.env.cr.dictfetchall():
            label = row["name"] or row["number"] or ""
            if row["number"] and row["number"] != label:
                label = "%s - %s" % (row["number"], label)
            contracts.append({
                "id": row["id"],
                "name": label,
                "partner_name": row["partner_name"] or "",
            })
        category_where, category_params = self._base_where(payload, include_category=False)
        self.env.cr.execute("""
            SELECT DISTINCT
                pc.id AS id,
                pc.name AS name,
                lower(pc.name) AS sort_name
            {from_sql}
            WHERE {where_sql}
                AND pc.id IS NOT NULL
            ORDER BY sort_name
        """.format(
            from_sql=self._from_sql(payload),
            where_sql=" AND ".join(category_where),
            rev_type_sql=rev_type_sql,
        ), category_params)
        categories = [{"id": r["id"], "name": r["name"] or ""} for r in self.env.cr.dictfetchall()]

        rev_types = ["Hosting", "Public Cloud", "M365", "Prof Serv", "Trading", "Not Set"]
        return {"partners": partners, "contracts": contracts, "categories": categories, "rev_types": rev_types}

    @api.model
    def view_report(self, payload=None):
        payload = self._normalize_payload(payload)
        months = self._months(payload["start_date"], payload["end_date"])
        month_keys = [m["key"] for m in months]
        where, params = self._base_where(payload)
        rev_type_sql = self._rev_type_sql()

        self.env.cr.execute("""
            SELECT
                pay.partner_id,
                rp.name AS partner_name,
                {rev_type_sql} AS rev_type,
                to_char(date_trunc('month', ml.period_to), 'YYYY-MM') AS month_key,
                SUM(COALESCE(ml.amount, 0.0)) AS amount,
                COUNT(DISTINCT cont.id) AS contract_count,
                COUNT(DISTINCT cont_line.id) AS service_count
            {from_sql}
            WHERE {where_sql}
            GROUP BY pay.partner_id, rp.name, {rev_type_sql}, date_trunc('month', ml.period_to)
            ORDER BY lower(rp.name), lower({rev_type_sql})
        """.format(
            rev_type_sql=rev_type_sql,
            from_sql=self._from_sql(payload),
            where_sql=" AND ".join(where),
        ), params)

        grouped = {}
        rev_types = set()
        totals = {key: 0.0 for key in month_keys}
        grand_total = 0.0

        for row in self.env.cr.dictfetchall():
            key = "%s|%s" % (row["partner_id"] or 0, row["rev_type"] or "")
            if key not in grouped:
                grouped[key] = {
                    "key": key,
                    "partner_id": row["partner_id"],
                    "partner_name": row["partner_name"] or "",
                    "rev_type": row["rev_type"] or "",
                    "months": {month_key: 0.0 for month_key in month_keys},
                    "total": 0.0,
                    "contract_count": 0,
                    "service_count": 0,
                    "unfoldable": True,
                }
            amount = float(row["amount"] or 0.0)
            month_key = row["month_key"]
            if month_key in grouped[key]["months"]:
                grouped[key]["months"][month_key] += amount
                grouped[key]["total"] += amount
                totals[month_key] += amount
                grand_total += amount
            grouped[key]["contract_count"] = max(grouped[key]["contract_count"], int(row["contract_count"] or 0))
            grouped[key]["service_count"] = max(grouped[key]["service_count"], int(row["service_count"] or 0))
            if row["rev_type"]:
                rev_types.add(row["rev_type"])

        summary = list(grouped.values())
        summary.sort(key=lambda r: ((r["partner_name"] or "").lower(), (r["rev_type"] or "").lower()))
        options = self._filter_options(payload)
        return {
            "months": months,
            "summary": summary,
            "totals": totals,
            "grand_total": grand_total,
            "rev_types": options["rev_types"],
            "partners": options["partners"],
            "contracts": options["contracts"],
            "categories": options["categories"],
            "date_range": {
                "start_date": payload["start_date"],
                "end_date": payload["end_date"],
            },
        }

    @api.model
    def get_row_lines(self, row_key, payload=None):
        payload = self._normalize_payload(payload)
        partner_id, rev_type = (row_key or "|").split("|", 1)
        payload["partner_id"] = int(partner_id or 0) or None
        payload["rev_type"] = rev_type or None

        months = self._months(payload["start_date"], payload["end_date"])
        month_keys = [m["key"] for m in months]
        where, params = self._base_where(payload)
        rev_type_sql = self._rev_type_sql()

        self.env.cr.execute("""
            SELECT
                cont.id AS contract_id,
                cont.name AS contract_number,
                cont.contract_code AS contract_name,
                cont.date_from,
                cont.date_to,
                cont_line.id AS contract_line_id,
                cont_line.name AS service_name,
                pt.name AS product_name,
                pay.billing_cycle,
                to_char(date_trunc('month', ml.period_to), 'YYYY-MM') AS month_key,
                SUM(COALESCE(ml.amount, 0.0)) AS amount,
                COUNT(ml.id) AS revenue_line_count
            {from_sql}
            WHERE {where_sql}
            GROUP BY
                cont.id, cont.name, cont.contract_code, cont.date_from, cont.date_to,
                cont_line.id, cont_line.name, pt.name, pay.billing_cycle,
                date_trunc('month', ml.period_to)
            ORDER BY cont.contract_code, cont.name, cont_line.id
        """.format(
            from_sql=self._from_sql(payload),
            where_sql=" AND ".join(where),
            rev_type_sql=rev_type_sql,
        ), params)

        grouped = {}
        for row in self.env.cr.dictfetchall():
            key = "%s|%s" % (row["contract_id"], row["contract_line_id"] or 0)
            if key not in grouped:
                grouped[key] = {
                    "key": key,
                    "contract_id": row["contract_id"],
                    "contract_number": row["contract_number"] or "",
                    "contract_name": row["contract_name"] or "",
                    "date_from": str(row["date_from"] or ""),
                    "date_to": str(row["date_to"] or ""),
                    "service_name": row["service_name"] or row["product_name"] or "",
                    "product_name": row["product_name"] or "",
                    "billing_cycle": row["billing_cycle"] or "",
                    "months": {month_key: 0.0 for month_key in month_keys},
                    "total": 0.0,
                    "revenue_line_count": 0,
                }
            amount = float(row["amount"] or 0.0)
            month_key = row["month_key"]
            if month_key in grouped[key]["months"]:
                grouped[key]["months"][month_key] += amount
                grouped[key]["total"] += amount
            grouped[key]["revenue_line_count"] += int(row["revenue_line_count"] or 0)

        return {"months": months, "lines": list(grouped.values())}

    @api.model
    def open_contracts(self, row_key, payload=None):
        payload = self._normalize_payload(payload)
        partner_id, rev_type = (row_key or "|").split("|", 1)
        payload["partner_id"] = int(partner_id or 0) or None
        payload["rev_type"] = rev_type or None

        where, params = self._base_where(payload)
        self.env.cr.execute("""
            SELECT DISTINCT cont.id AS contract_id
            {from_sql}
            WHERE {where_sql}
            ORDER BY cont.id
        """.format(
            from_sql=self._from_sql(payload),
            where_sql=" AND ".join(where),
        ), params)
        contract_ids = [row["contract_id"] for row in self.env.cr.dictfetchall() if row["contract_id"]]

        action = self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.action_od_asp_contract_view")
        action["domain"] = [("id", "in", contract_ids)]
        action["name"] = _("Contracts - %s") % (rev_type or _("Revenue Forecast"))
        return action

    @api.model
    def export_xlsx(self, payload=None):
        if not xlsxwriter:
            raise UserError(_("xlsxwriter is not installed."))

        report = self.view_report(payload)
        months = report["months"]
        rows = report["summary"]

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = wb.add_worksheet("Revenue Forecast")

        title_fmt = wb.add_format({"bold": True, "font_size": 14})
        hfmt = wb.add_format({"bold": True, "bg_color": "#C9C33C", "border": 1})
        text_fmt = wb.add_format({"border": 1})
        money_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1})
        total_fmt = wb.add_format({"bold": True, "num_format": "#,##0.00", "border": 1, "bg_color": "#F2F2F2"})

        ws.write(0, 0, "Revenue Forecast Report", title_fmt)
        ws.write(1, 0, "%s to %s" % (report["date_range"]["start_date"], report["date_range"]["end_date"]))

        headers = ["Client", "Rev Type"] + [m["label"] for m in months] + ["Total"]
        for col, header in enumerate(headers):
            ws.write(3, col, header, hfmt)

        for row_no, row in enumerate(rows, start=4):
            ws.write(row_no, 0, row["partner_name"], text_fmt)
            ws.write(row_no, 1, row["rev_type"], text_fmt)
            for idx, month in enumerate(months, start=2):
                ws.write_number(row_no, idx, float(row["months"].get(month["key"], 0.0)), money_fmt)
            ws.write_number(row_no, len(months) + 2, float(row["total"]), money_fmt)

        total_row = len(rows) + 4
        ws.write(total_row, 0, "Total", hfmt)
        ws.write(total_row, 1, "", hfmt)
        for idx, month in enumerate(months, start=2):
            ws.write_number(total_row, idx, float(report["totals"].get(month["key"], 0.0)), total_fmt)
        ws.write_number(total_row, len(months) + 2, float(report["grand_total"]), total_fmt)

        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 18)
        ws.set_column(2, len(months) + 2, 14)
        wb.close()
        output.seek(0)

        dr = report["date_range"]
        filename = "Revenue_Forecast_Report_%s_to_%s.xlsx" % (dr["start_date"], dr["end_date"])

        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "res_model": self._name,
            "res_id": 0,
        })
        return {
            "url": "/web/content/%s?download=true" % attachment.id,
            "filename": attachment.name,
        }
