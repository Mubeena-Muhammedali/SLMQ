from datetime import datetime

from odoo import api, fields, models


# ---------------------------------------------------------
# VEHICLE
# ---------------------------------------------------------
class GarageVehicle(models.Model):
    _name = 'garage.vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Garage Vehicle'
    _rec_name = 'plate_no'

    plate_no = fields.Char(string='Plate Number', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    vin_no = fields.Char(string='VIN / Chassis Number', tracking=True)
    brand_id = fields.Many2one('garage.brand', string='Brand', tracking=True)
    model_id = fields.Many2one(
        'garage.vehicle.model',
        string='Model',
        tracking=True,
        domain="[('brand_id', '=', brand_id)]",
    )
    colour = fields.Char(string='Colour', tracking=True)
    year = fields.Selection(selection='_get_year_selection', string='Year', tracking=True)
    kms = fields.Char(string='KMS', tracking=True)
    active = fields.Boolean(default=True)

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in range(current_year, 1980, -1)]

# ---------------------------------------------------------
# BRAND
# ---------------------------------------------------------
class GarageBrand(models.Model):
    _name = 'garage.brand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Brand'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)

# ---------------------------------------------------------
# VEHICLE MODEL
# ---------------------------------------------------------
class GarageVehicleModel(models.Model):
    _name = 'garage.vehicle.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Model'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    brand_id = fields.Many2one(
        'garage.brand',
        string='Brand',
        required=True
    )
    active = fields.Boolean(default=True)


# ---------------------------------------------------------
# CHARGER TYPE
# ---------------------------------------------------------
class GarageChargerType(models.Model):
    _name = 'garage.charger.type'
    _description = 'Charger Type'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


# ---------------------------------------------------------
# SUB STATUS
# ---------------------------------------------------------
class GarageSubStatus(models.Model):
    _name = 'garage.sub.status'
    _description = 'Job Sub Status'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


# ---------------------------------------------------------
# VEHICLE ENGINE
# ---------------------------------------------------------
class GarageVehicleEngine(models.Model):
    _name = 'garage.vehicle.engine'
    _description = 'Vehicle Engine'

    name = fields.Char(required=True)


# ---------------------------------------------------------
# CYLINDER
# ---------------------------------------------------------
class GarageCylinder(models.Model):
    _name = 'garage.cylinder'
    _description = 'Cylinder Type'

    name = fields.Char(required=True)


# ---------------------------------------------------------
# JOB CATEGORY
# ---------------------------------------------------------
class GarageJobCategory(models.Model):
    _name = 'garage.job.category'
    _description = 'Job Category'

    name = fields.Char(required=True)


# ---------------------------------------------------------
# ORDER TYPE
# ---------------------------------------------------------
class GarageOrderType(models.Model):
    _name = 'garage.order.type'
    _description = 'Order Type'

    name = fields.Char(required=True)


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------
class GarageStatus(models.Model):
    _name = 'garage.status'
    _description = 'Job Status'

    name = fields.Char(required=True)


# ---------------------------------------------------------
# LEAD SOURCE
# ---------------------------------------------------------
class GarageLeadSource(models.Model):
    _name = 'garage.lead.source'
    _description = 'Lead Source'

    name = fields.Char(required=True)
