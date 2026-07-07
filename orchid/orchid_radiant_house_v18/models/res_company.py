# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    od_ink_id = fields.Many2one('product.product', string="Ink Product")
    od_overhead_journal_id = fields.Many2one('account.journal', string="Overhead Journal")
    od_production_acc_id = fields.Many2one('account.account', string="Production Account")
    od_overhead_product_id = fields.Many2one('product.product', string="Overhead Product")
    od_overhead_account_id = fields.Many2one('account.account', string="Overhead Account")
    def_slitting_loc_id = fields.Many2one('stock.location', string="Slitting Location")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    od_ink_id = fields.Many2one('product.product', string="Ink Product", related='company_id.od_ink_id', readonly=False)
    od_overhead_journal_id = fields.Many2one('account.journal', string="Overhead Journal", related='company_id.od_overhead_journal_id', readonly=False)
    od_production_acc_id = fields.Many2one('account.account', string="Production Account", related='company_id.od_production_acc_id', readonly=False)
    od_overhead_product_id = fields.Many2one('product.product', string="Overhead Product", related='company_id.od_overhead_product_id', readonly=False)
    od_overhead_account_id = fields.Many2one('account.account', string="Overhead Account", related='company_id.od_overhead_account_id', readonly=False)
    def_slitting_loc_id = fields.Many2one('stock.location', string="Slitting Location", related='company_id.def_slitting_loc_id', readonly=False)
