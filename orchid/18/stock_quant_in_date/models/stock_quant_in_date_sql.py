# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class OdStockQuantInDate(models.Model):
    _name = 'od.stock.quant.in.date'
    _description = 'Stock Quant In-Date Breakdown'
    _auto = False
    _order = 'in_date desc'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', readonly=True)
    in_date = fields.Date(string='In Date', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    reserved_qty = fields.Float(string='Reserved Quantity', readonly=True)
    value = fields.Monetary(string='Value', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    # previously added fields
    brand_id = fields.Many2one('x_orchid_brand', string='Brand', readonly=True)
    classification_id = fields.Many2one('x_orchid_classificatio', string='Classification', readonly=True)
    group_id = fields.Many2one('x_orchid_group', string='Group', readonly=True)
    cost_method = fields.Selection(
        selection=[
            ('standard', 'Standard Price'),
            ('fifo', 'First In First Out (FIFO)'),
            ('average', 'Average Cost (AVCO)'),
        ],
        string='Costing Method',
        readonly=True,
    )
    inventory_quantity_set = fields.Boolean(string='Inventory Quantity Set', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)

    tracking = fields.Selection(
        selection=[
            ('serial', 'By Unique Serial Number'),
            ('lot', 'By Lots'),
            ('none', 'No Tracking'),
        ],
        string='Tracking',
        readonly=True,
    )
    type_id = fields.Many2one('x_orchid_type', string='Type', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    inventory_quantity = fields.Float(string='Counted Quantity', readonly=True)
    inventory_diff_quantity = fields.Float(string='Difference', readonly=True)

    # mirrors stock.quant's non-stored computed fields, same formulas as core:
    # available_quantity = quantity - reserved_quantity  (_compute_available_quantity)
    # inventory_quantity_auto_apply = quantity            (_compute_inventory_quantity_auto_apply)
    available_quantity = fields.Float(string='Available Quantity', readonly=True)
    inventory_quantity_auto_apply = fields.Float(string='Inventoried Quantity', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_sml_perf_in_date_idx
                ON stock_move_line (product_id, location_dest_id, state, date DESC);
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH anchor AS (
                    SELECT
                        q.product_id,
                        q.location_id,
                        q.lot_id,
                        q.company_id,
                        SUM(q.quantity) AS anchor_qty,
                        SUM(q.reserved_quantity) AS anchor_reserved,
                        MAX(q.in_date)::date AS fallback_in_date,
                        SUM(COALESCE(q.value, 0)) AS anchor_value,
                        BOOL_OR(q.value IS NOT NULL) AS anchor_has_value,
                        BOOL_OR(q.inventory_quantity_set) AS anchor_inventory_quantity_set,
                        -- these are quantity-like fields: sum across quants like quantity/
                        -- reserved_qty, then prorate across in-date cohorts the same way
                        SUM(q.inventory_quantity) AS anchor_inventory_quantity,
                        SUM(q.inventory_diff_quantity) AS anchor_inventory_diff_quantity
                    FROM stock_quant q
                    JOIN stock_location loc ON loc.id = q.location_id
                    JOIN product_product pp ON pp.id = q.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE loc.usage = 'internal'
                      AND q.quantity > 0
                      AND pp.active IS TRUE
                      AND pt.active IS TRUE
                    GROUP BY q.product_id, q.location_id, q.lot_id, q.company_id
                ),
                -- Per current-stock combo (product/location/lot/company), pull only
                -- the most recent receipt dates via an index-backed LATERAL lookup,
                -- capped at 30 dates, instead of joining/aggregating the ENTIRE
                -- stock_move_line history for every product up front. Each LATERAL
                -- call is a narrow, indexed lookup (product_id + location_dest_id
                -- equality, ORDER BY date DESC), so cost no longer scales with the
                -- total size of stock_move_line, only with the number of
                -- current-stock combos (rows in `anchor`) and a small constant (30).
                -- a.location_id is already a current, active internal location
                -- (guaranteed by the `anchor` WHERE clause above), so there's no
                -- need to re-check the destination location's usage/active flags
                -- here.
                cohort_calc AS (
                    SELECT
                        a.product_id,
                        a.location_id,
                        a.lot_id,
                        a.company_id,
                        a.anchor_qty,
                        a.anchor_reserved,
                        a.fallback_in_date,
                        a.anchor_value,
                        a.anchor_has_value,
                        a.anchor_inventory_quantity_set,
                        a.anchor_inventory_quantity,
                        a.anchor_inventory_diff_quantity,
                        x.in_date,
                        x.raw_qty
                    FROM anchor a
                    LEFT JOIN LATERAL (
                        SELECT
                            d.move_date AS in_date,
                            GREATEST(
                                0,
                                LEAST(d.qty, a.anchor_qty - (d.cum - d.qty))
                            ) AS raw_qty
                        FROM (
                            SELECT
                                sml.date::date AS move_date,
                                SUM(sml.quantity) AS qty,
                                SUM(SUM(sml.quantity)) OVER (
                                    ORDER BY sml.date::date DESC
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                                ) AS cum
                            FROM stock_move_line sml
                            WHERE sml.product_id = a.product_id
                              AND sml.location_dest_id = a.location_id
                              AND sml.lot_id IS NOT DISTINCT FROM a.lot_id
                              AND sml.state = 'done'
                            GROUP BY sml.date::date
                            ORDER BY sml.date::date DESC
                            LIMIT 30
                        ) d
                        -- skip dates that are already fully covered by more recent receipts
                        WHERE (d.cum - d.qty) < a.anchor_qty
                    ) x ON TRUE
                ),
                raw_totals AS (
                    SELECT product_id, lot_id, location_id, SUM(raw_qty) AS raw_total
                    FROM cohort_calc
                    WHERE raw_qty IS NOT NULL AND raw_qty > 0
                    GROUP BY product_id, lot_id, location_id
                ),
                product_cost AS (
                    SELECT
                        pp.id AS product_id,
                        pt.company_id AS template_company_id,
                        pp.standard_price AS standard_price_json,
                        pt.x_studio_brand AS brand_id,
                        pt.x_studio_classification AS classification_id,
                        pt.x_studio_group AS group_id,
                        pt.categ_id AS categ_id,
                        pt.tracking AS tracking,
                        pt.x_studio_type AS type_id,
                        pt.uom_id AS uom_id,
                        pcat.property_cost_method AS cost_method_json
                    FROM product_product pp
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    LEFT JOIN product_category pcat ON pcat.id = pt.categ_id
                ),
                scaled AS (
                    SELECT
                        cc.product_id,
                        cc.location_id,
                        cc.lot_id,
                        cc.company_id,
                        cc.in_date,
                        cc.anchor_qty * cc.raw_qty / rt.raw_total AS quantity,
                        cc.anchor_reserved * cc.raw_qty / rt.raw_total AS reserved_qty,
                        cc.anchor_value * cc.raw_qty / rt.raw_total AS anchor_value_share,
                        cc.anchor_has_value AS anchor_has_value,
                        cc.anchor_inventory_quantity_set AS inventory_quantity_set,
                        cc.anchor_inventory_quantity * cc.raw_qty / rt.raw_total AS inventory_quantity,
                        cc.anchor_inventory_diff_quantity * cc.raw_qty / rt.raw_total AS inventory_diff_quantity
                    FROM cohort_calc cc
                    JOIN raw_totals rt
                        ON rt.product_id = cc.product_id
                       AND rt.location_id = cc.location_id
                       AND rt.lot_id IS NOT DISTINCT FROM cc.lot_id
                    WHERE cc.raw_qty IS NOT NULL AND cc.raw_qty > 0
                ),
                fallback AS (
                    SELECT
                        a.product_id,
                        a.location_id,
                        a.lot_id,
                        a.company_id,
                        COALESCE(a.fallback_in_date, CURRENT_DATE) AS in_date,
                        a.anchor_qty AS quantity,
                        a.anchor_reserved AS reserved_qty,
                        a.anchor_value AS anchor_value_share,
                        a.anchor_has_value AS anchor_has_value,
                        a.anchor_inventory_quantity_set AS inventory_quantity_set,
                        a.anchor_inventory_quantity AS inventory_quantity,
                        a.anchor_inventory_diff_quantity AS inventory_diff_quantity
                    FROM anchor a
                    LEFT JOIN raw_totals rt
                        ON rt.product_id = a.product_id
                       AND rt.location_id = a.location_id
                       AND rt.lot_id IS NOT DISTINCT FROM a.lot_id
                       AND rt.raw_total > 0.000001
                    WHERE rt.product_id IS NULL
                ),
                combined AS (
                    SELECT * FROM scaled
                    UNION ALL
                    SELECT * FROM fallback
                )
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY comb.product_id, comb.location_id, comb.lot_id, comb.in_date
                    ) AS id,
                    comb.product_id AS product_id,
                    comb.location_id AS location_id,
                    comb.lot_id AS lot_id,
                    comb.in_date AS in_date,
                    comb.quantity AS quantity,
                    comb.reserved_qty AS reserved_qty,
                    CASE 
                        WHEN comb.anchor_has_value THEN comb.anchor_value_share
                        ELSE comb.quantity * COALESCE(
                            (pcost.standard_price_json ->> COALESCE(comb.company_id, pcost.template_company_id)::text)::numeric,
                            (pcost.standard_price_json ->> 'False')::numeric,
                            (
                                SELECT (kv.value)::numeric
                                FROM jsonb_each_text(pcost.standard_price_json) AS kv
                                LIMIT 1
                            ),
                            0
                        )
                    END AS value,
                    comp.currency_id AS currency_id,
                    comb.company_id AS company_id,
                    pcost.brand_id AS brand_id,
                    pcost.classification_id AS classification_id,
                    pcost.group_id AS group_id,
                    pcost.categ_id AS categ_id,
                    pcost.tracking AS tracking,
                    pcost.type_id AS type_id,
                    loc.warehouse_id AS warehouse_id,
                    pcost.uom_id AS uom_id,
                    COALESCE(
                        pcost.cost_method_json ->> COALESCE(comb.company_id, pcost.template_company_id)::text,
                        pcost.cost_method_json ->> 'False',
                        (
                            SELECT kv.value
                            FROM jsonb_each_text(pcost.cost_method_json) AS kv
                            LIMIT 1
                        )
                    ) AS cost_method,
                    comb.inventory_quantity_set AS inventory_quantity_set,
                    comb.inventory_quantity AS inventory_quantity,
                    comb.inventory_diff_quantity AS inventory_diff_quantity,
                    -- derived the same way core stock.quant computes them, from the
                    -- quantity/reserved_qty that are already correctly split/scaled
                    -- across in-date cohorts above
                    (comb.quantity - comb.reserved_qty) AS available_quantity,
                    comb.quantity AS inventory_quantity_auto_apply
                FROM combined comb
                JOIN product_cost pcost
                    ON pcost.product_id = comb.product_id
                LEFT JOIN res_company comp
                    ON comp.id = comb.company_id
                LEFT JOIN stock_location loc
                    ON loc.id = comb.location_id
            )
        """ % self._table)