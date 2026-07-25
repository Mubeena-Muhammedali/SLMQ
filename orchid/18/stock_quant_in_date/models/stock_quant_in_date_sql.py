# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class OdStockQuantInDateSql(models.Model):
    _name = 'od.stock.quant.in.date.sql'
    _description = 'Stock Quant In-Date Breakdown (SQL / FIFO window function)'
    _auto = False
    _order = 'in_date desc'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    in_date = fields.Date(string='In Date', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Supporting index for the underlying table this view reads from.
        # (Safe to run repeatedly - IF NOT EXISTS guards it.)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS od_sml_boundary_idx
                ON stock_move_line (state, product_id, location_id, location_dest_id, date)
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH base AS (
                    -- Single pass over stock_move_line, joined once to
                    -- stock_location on each side, tagging whether the
                    -- source/destination are internal. Rows where neither
                    -- side is internal (e.g. scrap-to-scrap) are dropped
                    -- immediately since they can never feed incoming or
                    -- outgoing below.
                    SELECT
                        sml.product_id AS product_id,
                        sml.location_dest_id AS dest_id,
                        sml.location_id AS src_id,
                        sml.date::date AS move_date,
                        sml.quantity AS quantity,
                        dest_loc.usage = 'internal' AS dest_is_internal,
                        src_loc.usage = 'internal' AS src_is_internal
                    FROM stock_move_line sml
                    JOIN stock_location dest_loc ON dest_loc.id = sml.location_dest_id
                    JOIN stock_location src_loc ON src_loc.id = sml.location_id
                    WHERE sml.state = 'done'
                      AND (dest_loc.usage = 'internal' OR src_loc.usage = 'internal')
                ),
                incoming AS (
                    -- Anything moving INTO an internal location is a receipt
                    -- for that location - whether it came from outside
                    -- (supplier, adjustment, production) or from another
                    -- internal location (a transfer).
                    SELECT
                        product_id,
                        dest_id AS location_id,
                        move_date,
                        SUM(quantity) AS qty
                    FROM base
                    WHERE dest_is_internal
                    GROUP BY product_id, dest_id, move_date
                ),
                outgoing AS (
                    -- Anything moving OUT of an internal location is an
                    -- issue for that location - whether it left to outside
                    -- (customer, scrap, adjustment) or to another internal
                    -- location (a transfer).
                    SELECT
                        product_id,
                        src_id AS location_id,
                        SUM(quantity) AS qty
                    FROM base
                    WHERE src_is_internal
                    GROUP BY product_id, src_id
                ),
                cohorts AS (
                    SELECT
                        i.product_id,
                        i.location_id,
                        i.move_date,
                        i.qty AS received_qty,
                        SUM(i.qty) OVER (
                            PARTITION BY i.product_id, i.location_id
                            ORDER BY i.move_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS cumulative_received
                    FROM incoming i
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY c.product_id, c.location_id, c.move_date) AS id,
                    c.product_id AS product_id,
                    c.location_id AS location_id,
                    c.move_date AS in_date,
                    GREATEST(
                        0,
                        LEAST(
                            c.received_qty,
                            c.cumulative_received - COALESCE(o.qty, 0)
                        )
                    ) AS quantity
                FROM cohorts c
                LEFT JOIN outgoing o
                    ON o.product_id = c.product_id AND o.location_id = c.location_id
            )
        """ % self._table)