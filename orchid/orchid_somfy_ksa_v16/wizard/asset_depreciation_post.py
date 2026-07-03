# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class OdAssetDepreciationPostWizard(models.TransientModel):
    _name = 'od.asset.depreciation.post.wizard'
    _description = 'Post Asset Depreciation Entries'

    od_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)

    def od_action_generate_depreciation_entries(self):
        self.ensure_one()

        moves = self.env['account.move'].search([
            ('company_id', '=', self.env.company.id),
            ('asset_id', '!=', False),
            ('state', '=', 'draft'),
            ('date', '<=', self.od_date),
        ], order='date asc, id asc')

        if not moves:
            raise UserError(_('No draft depreciation entries were found up to %s.') % self.od_date.strftime('%d/%m/%Y'))

        auto_post_moves = moves.filtered(lambda move: move.auto_post != 'no')
        if auto_post_moves:
            auto_post_moves.write({'auto_post': 'no'})

        moves.action_post()
        return {'type': 'ir.actions.act_window_close'}
