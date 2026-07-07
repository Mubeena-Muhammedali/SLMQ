# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class OdSpecialReqmaster(models.Model):
	_name = 'od.special.request'
	_description = "Special Master"

	name = fields.Char(string='Name', required=True)

class od_die_type_master(models.Model):
	_name = 'od.die.type.master'
	_description = "Die Master"

	name = fields.Char(string='Name', required=True)
	code = fields.Char(string='Code', required=True)
	description = fields.Text(string='Description')
	company_id = fields.Many2one('res.company', string="Company")

class OdDieMaterial(models.Model):
	_name = 'od.die.material'
	_description ='Die Material'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdDieLiner(models.Model):
	_name = 'od.die.liner'
	_description ='Die Liner'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdLiner(models.Model):
	_name = 'od.liner'
	_description ='Liner'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdDieMachine(models.Model):
	_name = 'od.die.machine'
	_description ='Die Machine'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdRawFaceStock(models.Model):
	_name = 'od.raw.face.stock'
	_description ='Raw Face Stock'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdRawFaceStockType(models.Model):
	_name = 'od.raw.face.stock.type'
	_description ='Raw Face Stock Type'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdRawAdhesive(models.Model):
	_name = 'od.raw.adhesive'
	_description ='Raw Adhesive'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdRawLiner(models.Model):
	_name = 'od.raw.liner'
	_description ='Raw Liner'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OdRCylinderTeeth(models.Model):
	_name = 'od.cylinder.teeth'
	_description ='cylinder Teeth'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")

class OrchidProductBrand(models.Model):
	_name = 'orchid.product.brand'
	_description = "Product Brand"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string="Company")

class OrchidProductType(models.Model):
	_name = 'orchid.product.type'
	_description = "Product Type"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string="Company")
	

class OrchidProductSubType(models.Model):
	_name = 'orchid.product.sub.type'
	_description = "Product Sub Type"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	type_id =  fields.Many2one('orchid.product.type', string='Type')
	company_id = fields.Many2one('res.company', string="Company")

class OrchidProductGroup(models.Model):
	_name = 'orchid.product.group'
	_description = "Product Group"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string="Company")

class OrchidProductSubGroup(models.Model):
	_name = 'orchid.product.sub.group'
	_description = "Product Sub Group"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	group_id =  fields.Many2one('orchid.product.group', string='Group')
	company_id = fields.Many2one('res.company', string="Company")

class OrchidProductClassification(models.Model):
	_name = 'orchid.product.classification'
	_description = "Product Classification"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string="Company")


class OdOverheadProduct(models.Model):
	_name  = 'od.over.head.product'
	_description = "Overhead Products for Machines"

	product_id  = fields.Many2one('product.product', string="Product")
	machine_id  = fields.Many2one('product.template', string="Machine")
	eval_code = fields.Text(string="Eval Code")
	company_id = fields.Many2one('res.company', string="Company")
	uom_id = fields.Many2one('uom.uom', string="Uom")

	@api.onchange('product_id')
	def onchange_product(self):
		for line in self:
			if line.product_id:
				line.eval_code = line.product_id.od_eval_code
			else:
				line.eval_code = False

class OdProductShape(models.Model):
	_name = 'od.product.shape'
	_description ='Product Shape'

	name = fields.Char(string='Name')
	company_id = fields.Many2one('res.company', string="Company")