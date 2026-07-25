# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    od_in_date_line_ids = fields.One2many(
        'od.stock.quant.in.date', 'quant_id', string='In-Date Breakdown'
    )

    @api.model
    def _update_available_quantity(
        self,
        product_id,
        location_id,
        quantity=None,
        reserved_quantity=None,
        lot_id=None,
        package_id=None,
        owner_id=None,
        in_date=None,
    ):
        result = super()._update_available_quantity(
            product_id=product_id,
            location_id=location_id,
            quantity=quantity,
            reserved_quantity=reserved_quantity,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            in_date=in_date,
        )

        if quantity:
            try:
                if quantity > 0:
                    # Genuine incoming quantity: add to (or start) today's/the
                    # given date's line.
                    self._log_in_date_breakdown(
                        product_id, location_id, quantity,
                        lot_id=lot_id, package_id=package_id,
                        owner_id=owner_id, in_date=in_date,
                    )
                else:
                    # Outgoing/consumed quantity: eat into the breakdown
                    # FIFO (oldest in_date first) so the lines always net
                    # to the quant's real on-hand quantity.
                    self._consume_in_date_breakdown(
                        product_id, location_id, quantity,
                        lot_id=lot_id, package_id=package_id,
                        owner_id=owner_id,
                    )
            except Exception:
                # Never let breakdown logging break the core stock flow
                _logger.exception(
                    "stock_quant_in_date: failed to update in-date breakdown "
                    "for product %s at location %s", product_id, location_id
                )

        return result

    def _log_in_date_breakdown(self, product_id, location_id, quantity, lot_id=None,
                                package_id=None, owner_id=None, in_date=None):
        quant = self._gather(
            product_id, location_id, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id, strict=True
        )[:1]
        if not quant:
            return

        date_key = (in_date or fields.Datetime.now())
        if hasattr(date_key, 'date'):
            date_key = date_key.date()

        line = quant.od_in_date_line_ids.filtered(lambda l: l.in_date == date_key)
        if line:
            line.quantity += quantity
        else:
            self.env['od.stock.quant.in.date'].sudo().create({
                'quant_id': quant.id,
                'in_date': date_key,
                'quantity': quantity,
            })

    def _consume_in_date_breakdown(self, product_id, location_id, quantity, lot_id=None,
                                    package_id=None, owner_id=None):
        """Reduce the in-date breakdown lines to reflect outgoing/consumed
        quantity. Consumes FIFO: the oldest in_date line is drawn down first,
        matching Odoo's own default removal strategy, so the sum of the
        remaining lines always matches the quant's actual on-hand quantity.
        """
        quant = self._gather(
            product_id, location_id, lot_id=lot_id,
            package_id=package_id, owner_id=owner_id, strict=True
        )[:1]
        if not quant:
            return

        qty_to_consume = abs(quantity)
        lines = quant.od_in_date_line_ids.sorted(key=lambda l: l.in_date)

        for line in lines:
            if qty_to_consume <= 0:
                break
            if line.quantity <= qty_to_consume:
                qty_to_consume -= line.quantity
                line.sudo().unlink()
            else:
                line.sudo().quantity -= qty_to_consume
                qty_to_consume = 0

    def action_backfill_in_date_breakdown(self):
        """Rebuild the in-date breakdown for existing quants from historical
        stock.move.line records. Safe to re-run any time (it wipes and
        rebuilds the lines for the quants in self, or all quants if none
        are given)."""
        quants = self or self.search([])
        InDate = self.env['od.stock.quant.in.date'].sudo()

        for quant in quants:
            domain = [
                ('product_id', '=', quant.product_id.id),
                ('location_dest_id', '=', quant.location_id.id),
                ('state', '=', 'done'),
            ]
            # Only count real incoming moves: source is external/supplier,
            # inventory adjustment, production, etc. - not another internal
            # location of the same warehouse (avoid inflating with transfers).
            domain.append(('location_id.usage', '!=', 'internal'))
            if quant.lot_id:
                domain.append(('lot_id', '=', quant.lot_id.id))
            if quant.package_id:
                domain.append(('result_package_id', '=', quant.package_id.id))
            if quant.owner_id:
                domain.append(('owner_id', '=', quant.owner_id.id))

            move_lines = self.env['stock.move.line'].search(domain)

            breakdown = {}
            for ml in move_lines:
                move_date = ml.date
                if not move_date:
                    continue
                d = move_date.date()
                qty = ml.qty_done if 'qty_done' in ml._fields else ml.quantity
                breakdown[d] = breakdown.get(d, 0.0) + qty

            # The moves above only capture genuine incoming receipts, so their
            # total will generally be >= the quant's current on-hand quantity
            # (the difference is whatever has since been consumed/shipped
            # out). Net that consumed amount off FIFO - oldest dates first -
            # so the rebuilt lines always sum to the real on-hand quantity.
            total_received = sum(breakdown.values())
            consumed = total_received - quant.quantity
            if consumed > 0:
                for d in sorted(breakdown.keys()):
                    if consumed <= 0:
                        break
                    if breakdown[d] <= consumed:
                        consumed -= breakdown[d]
                        breakdown[d] = 0.0
                    else:
                        breakdown[d] -= consumed
                        consumed = 0.0

            # Wipe old lines for this quant and rebuild clean
            InDate.search([('quant_id', '=', quant.id)]).unlink()
            for d, qty in breakdown.items():
                if qty:
                    InDate.create({
                        'quant_id': quant.id,
                        'in_date': d,
                        'quantity': qty,
                    })
