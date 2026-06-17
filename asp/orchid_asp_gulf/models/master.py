# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidProvisionServiceType(models.Model):
	_name = "od.provision.service.type"
	_description = "Provision Service Type"

	name=fields.Char(string="Service Type")

class OrchidProvisionType(models.Model):
	_name = "od.provision.type"
	_description = "ProvisionType"

	name=fields.Char(string="Provision Type")

class OrchidGMComments(models.Model):
	_name = "od.gm.comments"
	_description = "GM Comments"

	name=fields.Char(string="GM Comments")

class OrchidFinanceCheck(models.Model):
	_name = "od.finance.check"
	_description = "Finance Check"

	name=fields.Char(string="Finance Check")


class OrchidAzzuranceCluster(models.Model):
	_name = "od.azzurance.cluster"
	_description = "Azzurance Cluster"

	name=fields.Char(string="Azzurance Cluster")

class OrchidDiskMaster(models.Model):
	_name = "od.disk.master"
	_description = "Disk"

	name=fields.Char(string="Disk")

class OrchidDiskQty(models.Model):
	_name = "od.disk.qty"
	_description = "Disk Quantity"

	name=fields.Float(string="Disk Quantity")

class OrchidOSMaster(models.Model):
	_name = "od.os.master"
	_description = "OS"

	name=fields.Char(string="OS")

class OrchidLicense(models.Model):
	_name = "od.license"
	_description = "License"

	name=fields.Char(string="License")

class UtmMedium(models.Model):
	_inherit = "utm.medium"

	od_channel_id = fields.Many2one('utm.campaign', string="Channel")

class UtmSource(models.Model):
	_inherit = "utm.source"

	od_channel_id = fields.Many2one('utm.campaign', string="Channel")
	active = fields.Boolean(string="Active", default=True)

class UtmCampaign(models.Model):
	_inherit = "utm.campaign"

	active = fields.Boolean(string="Active", default=True)
