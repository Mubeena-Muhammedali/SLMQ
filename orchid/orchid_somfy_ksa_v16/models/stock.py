from odoo import api, fields, models, _

# for gulf saleupload purpose
class WarehouseStock(models.Model):
	_inherit = 'stock.warehouse'

	od_code = fields.Char(string="Code")

class StockQuant(models.Model):
	_inherit='stock.quant'

	od_value = fields.Float(string="Inventory Value", help="copy of odoo field value. For the purpose of reports.")

	@api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
	def _compute_value(self):
		res = super(StockQuant, self)._compute_value()
		for record in self:
			record.od_value = record.value
		return res

