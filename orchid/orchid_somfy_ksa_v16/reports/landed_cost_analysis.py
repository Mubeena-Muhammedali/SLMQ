from odoo import fields,models,api,_
from odoo import tools

class OrchidLandedCostAnalysis(models.Model):
    _name = 'od.landed.cost.analysis'
    _description = 'Landed Cost Analysis'
    _auto = False
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)

    move_date = fields.Date(readonly=True)

    total_cost = fields.Monetary(readonly=True)
    landed_cost = fields.Monetary(readonly=True)
    product_cost = fields.Monetary()

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW od_landed_cost_analysis AS (
                SELECT
                    MIN(aml.id) AS id,
                    aml.product_id,
                    am.company_id,
                    am.date AS move_date,

                    SUM(
                        CASE
                            -- WHEN aml.account_id = pc.property_stock_valuation_account_id
                            WHEN aml.account_id = 4465
                            THEN aml.debit - aml.credit
                            ELSE 0
                        END
                    ) AS total_cost,

                    SUM(
                        CASE
                            -- WHEN am.journal_id = rc.landed_cost_journal_id
                            WHEN am.journal_id = 34
                                 -- AND aml.account_id != pc.property_stock_valuation_account_id
                                 AND aml.account_id = 4465
                            THEN aml.debit - aml.credit
                            ELSE 0
                        END
                    ) AS landed_cost,

                    SUM(
                        CASE
                            WHEN aml.account_id = 4465
                            THEN aml.debit - aml.credit
                            ELSE 0
                        END
                    )
                    -
                    SUM(
                        CASE
                            WHEN am.journal_id = 34
                                 AND aml.account_id = 4465
                            THEN aml.debit - aml.credit
                            ELSE 0
                        END
                    ) AS product_cost

                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN product_product pp ON pp.id = aml.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN product_category pc ON pc.id = pt.categ_id
                JOIN res_company rc ON rc.id = am.company_id

                WHERE am.state = 'posted'
                  AND aml.product_id IS NOT NULL

                GROUP BY
                    aml.product_id,
                    am.date,
                    am.company_id
            )
        """)
