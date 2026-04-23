# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2026 IT-Solutions.mg. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wa_enabled = fields.Boolean(
        related="website_id.wa_enabled", readonly=False,
    )
    wa_phone = fields.Char(
        related="website_id.wa_phone", readonly=False,
    )
    wa_default_message = fields.Char(
        related="website_id.wa_default_message", readonly=False,
    )
    wa_tooltip = fields.Char(
        related="website_id.wa_tooltip", readonly=False,
    )
    wa_position = fields.Selection(
        related="website_id.wa_position", readonly=False,
    )
    wa_size = fields.Selection(
        related="website_id.wa_size", readonly=False,
    )
    wa_color = fields.Char(
        related="website_id.wa_color", readonly=False,
    )
    wa_pulse = fields.Boolean(
        related="website_id.wa_pulse", readonly=False,
    )
    wa_business_hours = fields.Boolean(
        related="website_id.wa_business_hours", readonly=False,
    )
    wa_hour_from = fields.Float(
        related="website_id.wa_hour_from", readonly=False,
    )
    wa_hour_to = fields.Float(
        related="website_id.wa_hour_to", readonly=False,
    )
    wa_days = fields.Char(
        related="website_id.wa_days", readonly=False,
    )
