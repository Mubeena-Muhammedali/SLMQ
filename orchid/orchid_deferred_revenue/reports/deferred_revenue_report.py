# -*- coding: utf-8 -*-
import base64
import io
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None


class OdDeferredRevenueReport(models.TransientModel):
    """Custom Deferred Revenue report, built entirely on top of
    od.contract.payment / od.contract.monthly.line (the module's own
    revenue-recognition schedule) instead of the base accounting
    deferred-revenue engine.

    A monthly line represents a slice of revenue for one period:
      - not invoiced yet                          -> "Not Started"
      - invoiced, recognition_date < period start  -> "Before"
      - invoiced, recognition_date inside period    -> current-period column
      - invoiced, recognition_date > period end     -> "Later"
      - "Recognized" = Before + current-period column (cumulative to date)

    Rows are grouped by the product's revenue/income account, mirroring the
    base Accounting > Reporting > Deferred Revenue screen (account rows,
    Total / Not Started / Before / <period> / Recognized / Later columns).
    """

    _name = "od.deferred.revenue.report"
    _description = "Deferred Revenue Report"

    # Stored filter snapshot, used only to carry the selected filters
    # through to the QWeb PDF report (which needs a record to iterate on).
    period = fields.Char(string="Period", default=lambda self: fields.Date.context_today(self).strftime("%Y-%m"))
    partner_id = fields.Many2one("res.partner", string="Customer")
    contract_id = fields.Many2one("od.asp.contract", string="Contract")
    journal_id = fields.Many2one("account.journal", string="Journal")
    group_by_account = fields.Boolean(string="Group by Account", default=True)
    # web.external_layout looks for this field on the record it's printing
    # to resolve the header/footer logo, address, VAT, bank details, etc.
    # Without it, the layout falls back silently and the PDF prints with
    # no company info at all.
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_drr_monthly_line_service_idx
            ON od_contract_monthly_line (service_id, recognition_date, invoiced)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_drr_contract_payment_partner_idx
            ON od_contract_payment (partner_id, contract_id, contract_line_id)
        """)

    # ---------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------
    def _normalize_payload(self, payload=None):
        payload = payload or {}
        period = payload.get("period") or fields.Date.context_today(self).strftime("%Y-%m")
        return {
            "period": period,
            "partner_id": payload.get("partner_id") or None,
            "contract_id": payload.get("contract_id") or None,
            "journal_id": payload.get("journal_id") or None,
            "group_by_account": payload.get("group_by_account", True),
            "only_active": payload.get("only_active", True),
        }

    def _period_bounds(self, period):
        import calendar
        year, month = [int(x) for x in period.split("-")]
        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)
        return start, end

    def _account_sql(self):
        # property_account_income_id / property_account_income_categ_id are
        # company_dependent fields: Odoo stores them as a jsonb column
        # ({"<company_id>": <account_id>, ...}), not a plain FK column, so
        # they must be unpacked with ->> and cast, keyed by the current
        # company id (passed in params as company_id_str).
        return """
            COALESCE(
                NULLIF(pt.property_account_income_id ->> %(company_id_str)s, '')::int,
                NULLIF(pcateg.property_account_income_categ_id ->> %(company_id_str)s, '')::int
            )
        """

    def _base_from_where(self, payload, start, end):
        params = {
            "company_id": self.env.company.id,
            "company_id_str": str(self.env.company.id),
            "period_start": start,
            "period_end": end,
        }
        where = ["cont.company_id = %(company_id)s"]
        # A specific contract was explicitly picked - show it regardless of
        # state (it may be terminated/completed but still carry deferred
        # revenue lines). Only apply the active-only default otherwise.
        if payload["only_active"] and not payload["contract_id"]:
            where.append("cont.state = 'active'")
        if payload["partner_id"]:
            params["partner_id"] = int(payload["partner_id"])
            where.append("pay.partner_id = %(partner_id)s")
        if payload["contract_id"]:
            params["contract_id"] = int(payload["contract_id"])
            where.append("cont.id = %(contract_id)s")
        if payload["journal_id"]:
            params["journal_id"] = int(payload["journal_id"])
            where.append("aml.journal_id = %(journal_id)s")
        from_sql = """
            FROM od_contract_monthly_line ml
            JOIN od_contract_payment pay ON pay.id = ml.service_id
            JOIN od_asp_contract cont ON cont.id = pay.contract_id
            LEFT JOIN od_asp_contract_line cont_line ON cont_line.id = pay.contract_line_id
            LEFT JOIN product_product pp ON pp.id = cont_line.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pcateg ON pcateg.id = pt.categ_id
            LEFT JOIN res_partner rp ON rp.id = pay.partner_id
            LEFT JOIN account_move_line aml ON aml.id = COALESCE(ml.invoice_line_id, ml.reverse_line_id)
            WHERE 1=1
        """
        return from_sql, where, params

    # ---------------------------------------------------------------
    # main report
    # ---------------------------------------------------------------
    @api.model
    def get_report(self, payload=None):
        payload = self._normalize_payload(payload)
        start, end = self._period_bounds(payload["period"])
        account_sql = self._account_sql()
        from_sql, where, params = self._base_from_where(payload, start, end)

        query = """
            SELECT
                {account_sql} AS account_id,
                CASE WHEN ml.invoice_line_id IS NULL AND ml.reverse_line_id IS NULL THEN 'not_started'
                     WHEN ml.recognition_date < %(period_start)s THEN 'before'
                     WHEN ml.recognition_date > %(period_end)s THEN 'later'
                     ELSE 'period'
                END AS bucket,
                SUM(COALESCE(ml.amount, 0.0)) AS amount
            {from_sql}
            AND {where_sql}
            GROUP BY {account_sql}, bucket
        """.format(account_sql=account_sql, from_sql=from_sql, where_sql=" AND ".join(where))
        self.env.cr.execute(query, params)
        rows_raw = self.env.cr.dictfetchall()

        accounts = {a.id: a for a in self.env["account.account"].browse(
            [r["account_id"] for r in rows_raw if r["account_id"]]
        ).exists()}

        grouped = {}
        for r in rows_raw:
            acc_id = r["account_id"] or 0
            key = acc_id if payload["group_by_account"] else 0
            if key not in grouped:
                account = accounts.get(acc_id)
                grouped[key] = {
                    "account_id": acc_id,
                    "account_code": account.code if account else _("Undefined"),
                    "account_name": account.name if account else _("No Income Account"),
                    "not_started": 0.0,
                    "before": 0.0,
                    "period": 0.0,
                    "later": 0.0,
                }
            grouped[key][r["bucket"]] += float(r["amount"] or 0.0)

        rows = []
        totals = {"not_started": 0.0, "before": 0.0, "period": 0.0, "recognized": 0.0, "later": 0.0, "total": 0.0}
        for row in grouped.values():
            row["recognized"] = row["before"] + row["period"]
            row["total"] = row["not_started"] + row["before"] + row["period"] + row["later"]
            for k in ("not_started", "before", "period", "recognized", "later", "total"):
                totals[k] += row[k]
            rows.append(row)
        rows.sort(key=lambda r: (r["account_code"] or ""))

        return {
            "period": {
                "key": payload["period"],
                "label": start.strftime("%b %Y"),
                "start": str(start),
                "end": str(end),
            },
            "rows": rows,
            "totals": totals,
            "filters": self._filter_options(),
            "group_by_account": payload["group_by_account"],
        }

    def _filter_options(self):
        # Avoid model.read_group(): its dict-based signature was removed in
        # Odoo 18+ in favour of _read_group(). search_read + dedupe in
        # Python is a couple of extra rows of code but works on every
        # version without guessing which API is present.
        payments = self.env["od.contract.payment"].sudo().search_read(
            [("partner_id", "!=", False)], ["partner_id"], limit=None
        )
        partner_map = {}
        for p in payments:
            if p["partner_id"]:
                partner_map[p["partner_id"][0]] = p["partner_id"][1]
        partners = [{"id": pid, "name": name} for pid, name in partner_map.items()]
        partners.sort(key=lambda p: (p["name"] or "").lower())

        # Show every contract, not just currently active ones - a
        # terminated/completed contract can still have deferred revenue
        # lines that haven't finished recognizing. Also company-scope
        # explicitly since sudo() bypasses record rules, and drop the
        # previous 500-row cap that was silently hiding contracts.
        contracts = self.env["od.asp.contract"].sudo().search_read(
            [("company_id", "=", self.env.company.id)], ["id", "name"], limit=None
        )
        contracts.sort(key=lambda c: (c["name"] or "").lower())

        # Sale journals are what deferred-revenue invoices are posted
        # through; keep the list scoped to the current company like the
        # other filters.
        journals = self.env["account.journal"].sudo().search_read(
            [("company_id", "=", self.env.company.id), ("type", "=", "sale")],
            ["id", "name"],
            limit=None,
        )
        journals.sort(key=lambda j: (j["name"] or "").lower())

        return {
            "partners": partners,
            "contracts": [{"id": c["id"], "name": c["name"]} for c in contracts],
            "journals": [{"id": j["id"], "name": j["name"]} for j in journals],
        }

    @api.model
    def get_row_lines(self, account_id, bucket, payload=None):
        payload = self._normalize_payload(payload)
        start, end = self._period_bounds(payload["period"])
        account_sql = self._account_sql()
        from_sql, where, params = self._base_from_where(payload, start, end)

        bucket_sql = {
            "not_started": "ml.invoice_line_id IS NULL AND ml.reverse_line_id IS NULL",
            "before": "(ml.invoice_line_id IS NOT NULL OR ml.reverse_line_id IS NOT NULL) AND ml.recognition_date < %(period_start)s",
            "period": "(ml.invoice_line_id IS NOT NULL OR ml.reverse_line_id IS NOT NULL) AND ml.recognition_date >= %(period_start)s AND ml.recognition_date <= %(period_end)s",
            "later": "(ml.invoice_line_id IS NOT NULL OR ml.reverse_line_id IS NOT NULL) AND ml.recognition_date > %(period_end)s",
        }.get(bucket)
        if not bucket_sql:
            raise UserError(_("Unknown bucket: %s") % bucket)

        extra_where = list(where)
        extra_where.append(bucket_sql)
        if account_id:
            params["account_id"] = int(account_id)
            extra_where.append("({account_sql}) = %(account_id)s".format(account_sql=account_sql))

        query = """
            SELECT
                cont.name AS contract_name,
                rp.name AS partner_name,
                cont_line.name AS service_name,
                ml.period_from AS period_from,
                ml.period_to AS period_to,
                ml.amount AS amount,
                ml.recognition_date AS recognition_date,
                ml.invoiced AS invoiced,
                ml.reverse_line_id AS reverse_line_id,
                ml.reverse_date AS reverse_date,
                pay.contract_id AS contract_id
            {from_sql}
            AND {where_sql}
            ORDER BY cont.name, ml.period_from
            LIMIT 2000
        """.format(from_sql=from_sql, where_sql=" AND ".join(extra_where))
        self.env.cr.execute(query, params)
        lines = []
        for row in self.env.cr.dictfetchall():
            lines.append({
                "contract_name": row["contract_name"] or "",
                "partner_name": row["partner_name"] or "",
                "service_name": row["service_name"] or "",
                "period_from": str(row["period_from"] or ""),
                "period_to": str(row["period_to"] or ""),
                "amount": float(row["amount"] or 0.0),
                "recognition_date": str(row["recognition_date"] or ""),
                "invoiced": bool(row["invoiced"]),
                "is_credit_note": bool(row["reverse_line_id"]),
                "reverse_date": str(row["reverse_date"] or ""),
                "contract_id": row["contract_id"],
            })
        return {"lines": lines}

    @api.model
    def open_contracts(self, account_id, bucket, payload=None):
        payload = self._normalize_payload(payload)
        res = self.get_row_lines(account_id, bucket, payload)
        contract_ids = list({l["contract_id"] for l in res["lines"] if l["contract_id"]})
        action = self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.action_od_asp_contract_view")
        action["domain"] = [("id", "in", contract_ids)]
        action["name"] = _("Contracts - Deferred Revenue")
        return action

    # ---------------------------------------------------------------
    # exports
    # ---------------------------------------------------------------
    @api.model
    def export_xlsx(self, payload=None):
        if not xlsxwriter:
            raise UserError(_("xlsxwriter is not installed."))

        report = self.get_report(payload)
        rows = report["rows"]
        period = report["period"]

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = wb.add_worksheet("Deferred Revenue")

        title_fmt = wb.add_format({"bold": True, "font_size": 14})
        hfmt = wb.add_format({"bold": True, "bg_color": "#5B2A86", "font_color": "white", "border": 1})
        text_fmt = wb.add_format({"border": 1})
        money_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1})
        total_fmt = wb.add_format({"bold": True, "num_format": "#,##0.00", "border": 1, "bg_color": "#F2F2F2"})
        total_text_fmt = wb.add_format({"bold": True, "border": 1, "bg_color": "#F2F2F2"})

        ws.write(0, 0, "Deferred Revenue", title_fmt)
        ws.write(1, 0, period["label"])

        headers = ["Account", "Total", "Not Started", "Before", period["label"], "Recognized", "Later"]
        for col, header in enumerate(headers):
            ws.write(3, col, header, hfmt)

        row_no = 4
        for row in rows:
            ws.write(row_no, 0, "%s %s" % (row["account_code"] or "", row["account_name"] or ""), text_fmt)
            ws.write_number(row_no, 1, row["total"], money_fmt)
            ws.write_number(row_no, 2, row["not_started"], money_fmt)
            ws.write_number(row_no, 3, row["before"], money_fmt)
            ws.write_number(row_no, 4, row["period"], money_fmt)
            ws.write_number(row_no, 5, row["recognized"], money_fmt)
            ws.write_number(row_no, 6, row["later"], money_fmt)
            row_no += 1

        totals = report["totals"]
        ws.write(row_no, 0, "Total", total_text_fmt)
        ws.write_number(row_no, 1, totals["total"], total_fmt)
        ws.write_number(row_no, 2, totals["not_started"], total_fmt)
        ws.write_number(row_no, 3, totals["before"], total_fmt)
        ws.write_number(row_no, 4, totals["period"], total_fmt)
        ws.write_number(row_no, 5, totals["recognized"], total_fmt)
        ws.write_number(row_no, 6, totals["later"], total_fmt)

        ws.set_column(0, 0, 34)
        ws.set_column(1, 6, 16)
        wb.close()
        output.seek(0)

        filename = "Deferred_Revenue_%s.xlsx" % period["key"]
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

    def get_report_for_pdf(self):
        """Used by the QWeb PDF report template - rebuilds the report from
        this transient record's stored filter snapshot."""
        self.ensure_one()
        payload = {
            "period": self.period,
            "partner_id": self.partner_id.id or None,
            "contract_id": self.contract_id.id or None,
            "journal_id": self.journal_id.id or None,
            "group_by_account": self.group_by_account,
        }
        return self.get_report(payload)

    @api.model
    def export_pdf(self, payload=None):
        payload = self._normalize_payload(payload)
        record = self.create({
            "period": payload["period"],
            "partner_id": payload["partner_id"],
            "contract_id": payload["contract_id"],
            "journal_id": payload["journal_id"],
            "group_by_account": payload["group_by_account"],
            "company_id": self.env.company.id,
        })
        report = self.env.ref("orchid_deferred_revenue.action_report_od_deferred_revenue")
        return report.report_action(record)
