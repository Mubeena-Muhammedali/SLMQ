from odoo import fields,models,api,_

class PurchaseOrder(models.Model):
	_inherit='purchase.order'

	old_erp_id = fields.Integer(string="Old ERP ID")
	od_old_num = fields.Char(string='Old Number')

class PurchaseOrderLine(models.Model):
	_inherit='purchase.order.line'

	old_erp_id = fields.Integer(string="Old ERP ID")

class SaleOrder(models.Model):
	_inherit='sale.order'

	old_erp_id = fields.Integer(string="Old ERP ID")
	od_old_num = fields.Char(string='Old Number')

class SalerderLine(models.Model):
	_inherit='sale.order.line'

	old_erp_id = fields.Integer(string="Old ERP ID")

class Partner(models.Model):
	_inherit='res.partner'

	old_erp_id = fields.Integer(string="Old ERP ID")

class ProductTemplate(models.Model):
	_inherit='product.template'

	old_erp_id = fields.Integer(string="Old ERP ID")

class AccountMove(models.Model):
	_inherit='account.move'

	old_erp_id = fields.Integer(string="Old ERP Move ID")
	old_erp_invoice_id = fields.Integer(string="Old ERP Invoice ID")
	od_old_num = fields.Char(string='Old Number')

class AccountMoveLine(models.Model):
	_inherit='account.move.line'

	old_erp_id = fields.Integer(string="Old ERP Move Line ID")
	old_erp_invoice_line_id = fields.Integer(string="Old ERP Invoice Line ID")

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	old_erp_id = fields.Integer(string="Old ERP Move ID")
	od_old_num = fields.Char(string='Old Number')

class OrchidVolumeRebate(models.Model):
	_inherit = 'orchid.volume.rebate'

	old_erp_id = fields.Integer(string="Old ERP ID")
	od_old_num = fields.Char(string='Old Number')

class OrchidVolumeRebateLine(models.Model):
	_inherit = 'orchid.volume.rebate.line'

	old_erp_id = fields.Integer(string="Old ERP ID")

class Pricelist(models.Model):
	_inherit = 'product.pricelist'

	old_erp_id = fields.Integer(string="Old ERP ID")
	od_old_num = fields.Char(string='Old Number')

class PricelistItem(models.Model):
	_inherit = 'product.pricelist.item'

	old_erp_id = fields.Integer(string="Old ERP ID")
